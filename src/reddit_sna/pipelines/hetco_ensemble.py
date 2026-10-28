"""Pre-declared HeTCo v3: seed-averaged HeTCo probabilities mixed with B4.

The declaration file must be committed and unchanged before the run. Selection
reads only its declared months, which precede the test start. A B4+B5 mixture
with the same weights is the fairness control. B4/B5 are refitted with the
research settings, and their predictions must equal the research run's.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from time import perf_counter
import tomllib

import numpy as np

from reddit_sna.config import validate_run_id
from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.research import EVENTS, KEY, score
from reddit_sna.evaluation.research_protocol import FULL
from reddit_sna.models.hetco import HETCO, fit_hetco, predict_hetco
from reddit_sna.models.research import fit_variant
from reddit_sna.pipelines.hetco import community_delta, load_samples
from reddit_sna.pipelines.research import read_table, save_json, write_table

FIELDS = {"schema_version", "protocol_id", "class_weight", "head", "poolings", "weights", "partner",
          "control", "seed_aggregation", "selection_months", "selection_metric", "tie_break"}


def load_declaration(path, protocol):
    """Reject unknown fields, selection months at or after the test start, and uncommitted edits."""
    path = Path(path).resolve()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if set(data) != FIELDS or data["schema_version"] != 1 or data["seed_aggregation"] != "mean_probability":
        raise ValueError("HeTCo ensemble declaration fields differ from the supported schema")
    if (not data["selection_months"] or any(m >= protocol["test_start"] for m in data["selection_months"])
            or not set(data["selection_months"]) <= set(protocol["rolling_months"])):
        raise ValueError("Selection months must be declared rolling months before the test start")
    if sorted(data["weights"]) != data["weights"] or not all(0 <= w <= 1 for w in data["weights"]):
        raise ValueError("Ensemble weights must be ordered values in [0, 1]")
    root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=path.parent, check=True,
                               capture_output=True, text=True).stdout.strip())
    relative = path.relative_to(root.resolve()).as_posix()
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", relative], cwd=root, capture_output=True)
    clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", relative], cwd=root)
    if tracked.returncode or clean.returncode:
        raise ValueError("Commit the HeTCo ensemble declaration before running it")
    commit = subprocess.run(["git", "log", "-1", "--format=%H", "--", relative], cwd=root, check=True,
                            capture_output=True, text=True).stdout.strip()
    return data, dict(path=relative, sha256=digest_file(path), declared_in_commit=commit)


def _proba(model, matrix):
    """Six-event probabilities from an sklearn model; unseen classes get zero."""
    out = np.zeros((len(matrix), len(EVENTS)))
    for i, c in enumerate(model.classes_):
        out[:, EVENTS.index(c)] = model.predict_proba(matrix)[:, i]
    return out


def _choose(rows):
    """Highest score; ties prefer the smaller HeTCo weight, then attention."""
    return min(rows, key=lambda r: (-round(r["macro_f1_six"], 12), r["weight"], r["pooling"] != "attention"))


def run_hetco_ensemble(declaration, research_run, preparation, artifact_root, run_id):
    started = perf_counter()
    research_run, preparation, artifact_root = (Path(p).resolve() for p in (research_run, preparation, artifact_root))
    validate_run_id(run_id)
    output = artifact_root / "hetco" / run_id
    if output.exists() or not output.is_relative_to(artifact_root):
        raise ValueError("HeTCo ensemble output exists or escapes artifacts")
    source = json.loads((research_run / "manifest.json").read_text(encoding="utf-8"))
    if source.get("status") != "complete" or Path(source["source_preparation"]).resolve() != preparation:
        raise ValueError("HeTCo ensemble needs a complete research run built from this preparation")
    protocol = json.loads((research_run / "protocol.json").read_text(encoding="utf-8"))
    plan, declared = load_declaration(declaration, protocol)
    output.mkdir(parents=True)
    manifest = dict(status="started", schema_version=1, artifact_type="hetco-ensemble", declaration=declared,
                    settings=HETCO, exposure="inspected_development_data", unseen=False,
                    source_manifests={str(p): digest_file(p) for p in (research_run / "manifest.json",
                                                                         preparation / "manifest.json")})
    save_json(output / "manifest.json", manifest)
    try:
        (output / "declaration.toml").write_bytes(Path(declaration).read_bytes())
        samples = load_samples(research_run, preparation)
        reference = {(r["window"], r["model"], int(r["seed"]), *(r[k] for k in KEY)): r["y_pred"]
                     for r in read_table(research_run / "predictions.csv")
                     if r["model"] in (plan["partner"], plan["control"])}
        windows = [("main", protocol["test_start"]), *[("rolling", m) for m in protocol["rolling_months"]]]
        cache = {}
        for window, boundary in windows:
            train = [r for r in samples if r["label_month"] < boundary]
            test = [r for r in samples if (r["label_month"] >= boundary if window == "main"
                                           else r["label_month"] == boundary)]
            probabilities = {name: [] for name in (*plan["poolings"], plan["partner"], plan["control"])}
            for seed in protocol["seeds"]:
                for pooling in plan["poolings"]:
                    fitted = fit_hetco([r["bag"] for r in train], [[float(r[f]) for f in FULL] for r in train],
                                       [r["label"] for r in train], seed, pooling,
                                       class_weight=plan["class_weight"], head=plan["head"])
                    probabilities[pooling].append(predict_hetco(fitted, [r["bag"] for r in test],
                                                                [[float(r[f]) for f in FULL] for r in test])[1])
                for name in (plan["partner"], plan["control"]):
                    fitted = fit_variant(name, train, seed)
                    matrix = [[float(r[f]) for f in fitted["fields"]] for r in test]
                    proba = _proba(fitted["model"], matrix)
                    predicted = list(fitted["model"].predict(matrix))
                    if predicted != [reference[(window, name, seed, *(r[k] for k in KEY))] for r in test]:
                        raise ValueError(f"Refitted {name} differs from the research run")
                    probabilities[name].append(proba)
            cache[(window, boundary)] = (test, {k: np.mean(v, axis=0) for k, v in probabilities.items()})

        def mixed(key, member, weight, base):
            test, p = cache[key]
            return test, weight * p[member] + (1 - weight) * p[base]

        def rows_of(test, proba):
            return [dict(y_true=r["label"], y_pred=EVENTS[i], fallback=0) for r, i in zip(test, proba.argmax(axis=1))]

        selection_keys = [("rolling", m) for m in plan["selection_months"]]
        candidates, controls = [], []
        for pooling in plan["poolings"]:
            for weight in plan["weights"]:
                pooled = [x for key in selection_keys for x in rows_of(*mixed(key, pooling, weight, plan["partner"]))]
                candidates.append(dict(kind="hetco", pooling=pooling, weight=weight,
                                       macro_f1_six=score(pooled)["macro_f1_six"]))
        for weight in plan["weights"]:
            pooled = [x for key in selection_keys for x in rows_of(*mixed(key, plan["control"], weight, plan["partner"]))]
            controls.append(dict(kind="control", pooling="none", weight=weight, macro_f1_six=score(pooled)["macro_f1_six"]))
        chosen, control = _choose(candidates), _choose(controls)
        write_table(output / "selection.csv", candidates + controls)
        manifest.update(selected=chosen, selected_control=control,
                        selection_frozen_at=datetime.now(timezone.utc).isoformat())
        save_json(output / "manifest.json", manifest)

        models = {"B4_logreg": (plan["partner"], 0.0), "HeTCo_v2_seedavg": ("attention", 1.0),
                  "HeTCo_v3": (chosen["pooling"], chosen["weight"]), "Control_B4_B5": (plan["control"], control["weight"])}
        units, predictions, comparison = {}, [], []
        unselected = [m for m in protocol["rolling_months"] if m not in plan["selection_months"]]
        for name, (member, weight) in models.items():
            for window, boundary in windows:
                test, proba = mixed((window, boundary), member, weight, plan["partner"])
                for r, p in zip(test, proba):
                    predictions.append({**{k: r[k] for k in KEY}, "window": window, "model": name, "seed": 0,
                                        "y_true": r["label"], "y_pred": EVENTS[int(p.argmax())], "fallback": 0,
                                        **{f"proba_{e}": float(v) for e, v in zip(EVENTS, p)}})
        for name in models:
            for window, months in (("main", None), ("rolling_unselected", unselected), ("rolling_selection", plan["selection_months"])):
                rows = [r for r in predictions if r["model"] == name and (
                    r["window"] == "main" if window == "main" else r["window"] == "rolling" and r["label_month"] in months)]
                result = score(rows)
                comparison.append(dict(window=window, model=name, n=result["n"], macro_f1_six=result["macro_f1_six"],
                                       balanced_accuracy=result["balanced_accuracy"],
                                       **{f"f1_{e}": v["f1"] for e, v in result["per_class"].items()}))
            units[("main", name, 0)] = [r for r in predictions if r["model"] == name and r["window"] == "main"]
        intervals = [community_delta(units, a, b, [0]) for a, b in (
            ("HeTCo_v3", "B4_logreg"), ("Control_B4_B5", "B4_logreg"), ("HeTCo_v3", "Control_B4_B5"),
            ("HeTCo_v2_seedavg", "B4_logreg"))]
        write_table(output / "predictions.csv", predictions)
        write_table(output / "comparison.csv", comparison)
        save_json(output / "evaluation.json", dict(selected=chosen, selected_control=control,
                                                   comparison=comparison, main_intervals=intervals))
        manifest.update(status="complete", finished_at=datetime.now(timezone.utc).isoformat(),
                        wall_seconds=perf_counter() - started,
                        artifact_hashes={p.name: digest_file(p) for p in output.iterdir()
                                         if p.is_file() and p.name != "manifest.json"})
        save_json(output / "manifest.json", manifest)
    except BaseException as exc:
        manifest.update(status="failed", failure_type=type(exc).__name__, wall_seconds=perf_counter() - started)
        save_json(output / "manifest.json", manifest)
        raise
    return output
