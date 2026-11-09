"""Pre-declared HeTCo v5: v4 plus a tier-1 threshold chosen on inner origins.

The declaration must be committed and unchanged before the run. Every model
fit yields both its argmax decisions (v4 rule) and its thresholded decisions
(v5 rule), so the v5-v4 difference isolates the operating point. Hierarchical
LR on community attributes goes through the same procedure as the refuting
control. Selection reads only declared months before the test start.
"""

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from time import perf_counter
import tomllib

import numpy as np

from reddit_sna.artifacts import capture_run_provenance, source_snapshot
from reddit_sna.config import validate_run_id
from reddit_sna.contracts import next_month
from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.research import KEY, score
from reddit_sna.evaluation.research_protocol import FULL
from reddit_sna.models.hetco import EVENTS, HETCO, fit_hetco, predict_hetco, tier1_decision

FIELDS = {"schema_version", "protocol_id", "class_weight", "head", "members", "poolings", "control",
          "thresholds", "selection_months", "selection_metric", "tie_break", "placebo_stratum"}
# family -> (argmax model name, thresholded model name)
NAMES = {"attention": ("HeTCo_v4", "HeTCo_v5"), "mean": ("A7v4_mean_pool", "A7v5_mean_pool"),
         "LR_hier_community": ("LR_hier_community", "LR_hier_community_t1")}
REFERENCES = ("B4_logreg", "B5_matched_boosting")


def load_declaration(path, protocol, require_commit=True):
    """Reject unknown fields, late selection months, bad thresholds and uncommitted edits."""
    path = Path(path).resolve()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if set(data) != FIELDS or data["schema_version"] != 1 or data["selection_metric"] != "macro_f1_six":
        raise ValueError("HeTCo threshold declaration fields differ from the supported schema")
    fixed = dict(class_weight="balanced", head="hierarchical", members="extended",
                 poolings=["attention", "mean"], control="LR_hier_community",
                 tie_break="declaration_order", placebo_stratum="missing_no_shared")
    if any(data[name] != value for name, value in fixed.items()):
        raise ValueError("Threshold ablation must retain the declared v4 settings and controls")
    if (not data["selection_months"] or len(set(data["selection_months"])) != len(data["selection_months"])
            or any(m >= protocol["test_start"] for m in data["selection_months"])
            or not set(data["selection_months"]) <= set(protocol["rolling_months"])):
        raise ValueError("Selection months must be declared rolling months before the test start")
    if (not data["thresholds"] or data["thresholds"][0] != "argmax"
            or len(set(map(str, data["thresholds"]))) != len(data["thresholds"])):
        raise ValueError("Thresholds must start with the unchanged argmax rule and be distinct")
    for threshold in data["thresholds"]:
        tier1_decision(np.full((1, len(EVENTS)), 1 / len(EVENTS)), threshold)
    if set(data["poolings"]) - {"attention", "mean"} or data["control"] != "LR_hier_community":
        raise ValueError("Unsupported pooling or control")
    provenance = dict(path=str(path), sha256=digest_file(path))
    if require_commit:
        root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=path.parent, check=True,
                                   capture_output=True, text=True).stdout.strip()).resolve()
        relative = path.relative_to(root).as_posix()
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", relative], cwd=root, capture_output=True)
        clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", relative], cwd=root)
        if tracked.returncode or clean.returncode:
            raise ValueError("Commit the HeTCo threshold declaration before running it")
        commit = subprocess.run(["git", "log", "-1", "--format=%H", "--", relative], cwd=root, check=True,
                                capture_output=True, text=True).stdout.strip()
        provenance.update(path=relative, declared_in_commit=commit)
    return data, provenance


def _probabilities(family, declaration, train, test, seed):
    """Six-event probabilities of one fit; families share data, seed and budget."""
    if family == "LR_hier_community":
        from reddit_sna.models.activity_forecast import fit_activity_model, predict_activity_model
        from reddit_sna.pipelines.controlled_pooling import LR

        fitted = fit_activity_model(train, FULL, LR, hierarchical=True, seed=seed)
        return np.asarray(predict_activity_model(fitted, test)[1])
    bag = "bag_extended" if declaration["members"] == "extended" else "bag"
    fitted = fit_hetco([r[bag] for r in train], [[float(r[f]) for f in FULL] for r in train],
                       [r["label"] for r in train], seed, family,
                       class_weight=declaration["class_weight"], head=declaration["head"])
    return predict_hetco(fitted, [r[bag] for r in test], [[float(r[f]) for f in FULL] for r in test])[1]


def select_threshold(samples, declaration, family, seeds, fit=_probabilities):
    """Seed-mean macro-F1 of every declared threshold on pooled inner origins."""
    collected = {seed: ([], []) for seed in seeds}
    for month in declaration["selection_months"]:
        train = [r for r in samples if r["label_month"] < month]
        test = [r for r in samples if r["label_month"] == month]
        for seed in seeds:
            collected[seed][0].extend(r["label"] for r in test)
            collected[seed][1].append(fit(family, declaration, train, test, seed))
    rows = []
    for threshold in declaration["thresholds"]:
        values = []
        for seed in seeds:
            truth, parts = collected[seed]
            pred = tier1_decision(np.vstack(parts), threshold)
            values.append(score([dict(y_true=t, y_pred=p, fallback=0) for t, p in zip(truth, pred)])["macro_f1_six"])
        rows.append(dict(family=family, threshold=str(threshold), origins=" ".join(declaration["selection_months"]),
                         mean_macro_f1_six=float(np.mean(values))))
    best = max(range(len(rows)), key=lambda i: (rows[i]["mean_macro_f1_six"], -i))
    return rows, declaration["thresholds"][best]


def run_hetco_threshold(research_run, preparation, artifact_root, run_id, declaration_path,
                        reference_hetco_run=None, require_commit=True, fit=_probabilities):
    from reddit_sna.pipelines.controlled_pooling import LR, verify_run
    from reddit_sna.pipelines.hetco import _block_delta, community_delta, load_samples
    from reddit_sna.pipelines.research import read_table, save_json, write_table

    started = perf_counter()
    research_run, preparation, artifact_root = (Path(p).resolve() for p in (research_run, preparation, artifact_root))
    validate_run_id(run_id)
    output = artifact_root / "hetco" / run_id
    if output.exists() or not output.is_relative_to(artifact_root):
        raise ValueError("HeTCo output exists or escapes artifacts")
    source = json.loads((research_run / "manifest.json").read_text(encoding="utf-8"))
    if source.get("status") != "complete" or Path(source["source_preparation"]).resolve() != preparation:
        raise ValueError("HeTCo needs a complete research run built from this preparation")
    protocol = json.loads((research_run / "protocol.json").read_text(encoding="utf-8"))
    declaration, provenance = load_declaration(declaration_path, protocol, require_commit)
    if require_commit:
        verify_run(research_run, artifact_root)
        verify_run(preparation, artifact_root)
        if reference_hetco_run is not None:
            verify_run(reference_hetco_run, artifact_root)
    pins = {str(p): digest_file(p) for p in (research_run / "manifest.json", preparation / "manifest.json")}
    if reference_hetco_run is not None:
        reference_manifest = Path(reference_hetco_run).resolve() / "manifest.json"
        pins[str(reference_manifest)] = digest_file(reference_manifest)
    families = [*declaration["poolings"], declaration["control"]]
    windows = [("main", protocol["test_start"]), *[("rolling", m) for m in protocol["rolling_months"]]]
    plan = [dict(phase="selection", boundary=m, seed=s, family=f)
            for f in families for m in declaration["selection_months"] for s in protocol["seeds"]]
    plan += [dict(phase=w, boundary=m, seed=s, family=f)
             for w, m in windows for s in protocol["seeds"] for f in families]
    provenance_source, environment, blobs = capture_run_provenance()
    output.mkdir(parents=True)
    manifest = dict(status="started", schema_version=1, artifact_type="hetco-v5-threshold",
                    source_manifests=pins, declaration=provenance, settings=HETCO, lr_settings=LR,
                    families={f: list(NAMES[f]) for f in families}, references=list(REFERENCES),
                    exposure="inspected_development_data", unseen=False,
                    source=provenance_source, maximum_configuration_fits=len(plan), configuration_fits=0,
                    created_at=datetime.now(timezone.utc).isoformat())
    save_json(output / "manifest.json", manifest)
    fits = []
    try:
        for name, blob in blobs.items():
            target = output / "provenance/source" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
        save_json(output / "environment.json", environment)
        frozen_protocol = dict(declaration=declaration, research_protocol=protocol, fit_plan=plan,
                               settings=HETCO, lr_settings=LR, community_fields=list(FULL),
                               source_manifests=pins)
        save_json(output / "frozen-protocol.json", frozen_protocol)
        frozen_hash = digest_file(output / "frozen-protocol.json")
        manifest["frozen_protocol_sha256"] = frozen_hash
        save_json(output / "manifest.json", manifest)
        print(f"Frozen {len(plan)} fits before extraction/fitting", flush=True)
        samples = load_samples(research_run, preparation, extended=declaration["members"] == "extended")
        sample_keys = [tuple(r[k] for k in KEY) for r in samples]
        if (not samples or len(set(sample_keys)) != len(sample_keys)
                or any(r["label_month"] != next_month(r["feature_month"]) or r["label"] not in EVENTS
                       for r in samples)):
            raise ValueError("Samples need unique keys, consecutive target months and valid labels")
        for item in plan:
            if (not any(r["label_month"] < item["boundary"] for r in samples)
                    or not any(r["label_month"] == item["boundary"] for r in samples)):
                raise ValueError("Every declared origin needs training and test samples")

        def recorded_fit(phase, family, config, train, test, seed):
            boundary = min(r["label_month"] for r in test)
            item = dict(phase=phase, boundary=boundary, seed=seed, family=family)
            if len(fits) >= len(plan) or item != plan[len(fits)]:
                raise ValueError("Fit differs from frozen order or exceeds finite budget")
            if any(r["label_month"] >= boundary for r in train):
                raise ValueError("Training labels overlap evaluation origin")
            tick = perf_counter()
            probabilities = np.asarray(fit(family, config, train, test, seed), dtype=float)
            if (probabilities.shape != (len(test), len(EVENTS)) or not np.isfinite(probabilities).all()
                    or (probabilities < 0).any() or (probabilities > 1).any()
                    or not np.allclose(probabilities.sum(axis=1), 1)):
                raise ValueError("Fit must return finite normalized six-event probabilities")
            fits.append(dict(**item, train_n=len(train), test_n=len(test),
                             latest_train_label=max(r["label_month"] for r in train),
                             wall_seconds=perf_counter()-tick))
            save_json(output / "fits.json", fits)
            print(f"{len(fits)}/{len(plan)} {phase} {boundary} {seed} {family}", flush=True)
            return probabilities

        selection, chosen = [], {}
        for family in families:
            rows, chosen[family] = select_threshold(samples, declaration, family, protocol["seeds"],
                lambda f, c, tr, te, s: recorded_fit("selection", f, c, tr, te, s))
            selection += rows
        write_table(output / "selection.csv", selection)
        manifest.update(selected={f: str(t) for f, t in chosen.items()})
        save_json(output / "manifest.json", manifest)
        predictions = []
        for window, boundary in windows:
            train = [r for r in samples if r["label_month"] < boundary]
            test = [r for r in samples if (r["label_month"] >= boundary if window == "main"
                                           else r["label_month"] == boundary)]
            for seed in protocol["seeds"]:
                for family in families:
                    proba = recorded_fit(window, family, declaration, train, test, seed)
                    for name, threshold in zip(NAMES[family], ("argmax", chosen[family])):
                        predictions.extend({**{k: r[k] for k in KEY}, "window": window, "model": name, "seed": seed,
                                            "y_true": r["label"], "y_pred": p, "fallback": 0,
                                            **{f"p_{event}": float(q[i]) for i, event in enumerate(EVENTS)}}
                                           for r, p, q in zip(test, tier1_decision(proba, threshold), proba))
        write_table(output / "predictions.csv", predictions)
        if reference_hetco_run:
            stored = {(r["window"], r["model"], int(r["seed"]), *(r[k] for k in KEY)): r["y_pred"]
                      for r in read_table(Path(reference_hetco_run) / "predictions.csv")}
            refit = [(stored.get((r["window"], r["model"], r["seed"], *(r[k] for k in KEY))), r["y_pred"])
                     for r in predictions if r["model"] in ("HeTCo_v4", "A7v4_mean_pool")]
            manifest["refit_matches_reference"] = dict(
                run=str(Path(reference_hetco_run).resolve()), rows=len(refit),
                found=sum(a is not None for a, _ in refit), equal=sum(a == b for a, b in refit))
            if any(a is None or a != b for a, b in refit):
                raise ValueError("Argmax refit differs from archived reference predictions")
        reference_rows = [r for r in read_table(research_run / "predictions.csv") if r["model"] in REFERENCES]
        for r in reference_rows:
            r["seed"], r["fallback"] = int(r["seed"]), int(r["fallback"])
        units, monthly = defaultdict(list), defaultdict(list)
        for r in reference_rows + predictions:
            units[(r["window"], r["model"], r["seed"])].append(r)
            if r["window"] == "rolling":
                monthly[(r["model"], r["seed"], r["label_month"])].append(r)
        for window in ("main", "rolling"):
            keys = {frozenset(tuple(r[k] for k in KEY) for r in rows)
                    for (w, _, _), rows in units.items() if w == window}
            if len(keys) != 1:
                raise ValueError("Threshold and reference predictions must cover identical samples")
        models = [name for f in families for name in NAMES[f]]
        comparison = []
        for window in ("main", "rolling"):
            for name in (*REFERENCES, *models):
                values = [score(units[(window, name, s)]) for s in protocol["seeds"]]
                comparison.append(dict(window=window, model=name, n_per_seed=values[0]["n"],
                                       mean_macro_f1_six=float(np.mean([v["macro_f1_six"] for v in values])),
                                       per_seed=" ".join(f"{v['macro_f1_six']:.4f}" for v in values),
                                       mean_balanced_accuracy=float(np.mean([v["balanced_accuracy"] for v in values]))))
        # Ablation: each thresholded model against its own argmax fit; primary and control against references.
        pairs = [(NAMES[f][1], NAMES[f][0]) for f in families]
        pairs += [(name, ref) for name in ("HeTCo_v5", "HeTCo_v4") if name in models for ref in REFERENCES]
        pairs += [("HeTCo_v5", "LR_hier_community_t1")] if "HeTCo_v5" in models else []
        intervals = [_block_delta(monthly, protocol["rolling_months"], a, b, protocol["seeds"], protocol["bootstrap"])
                     for a, b in pairs]
        main_intervals = [community_delta(units, a, b, protocol["seeds"]) for a, b in pairs]
        write_table(output / "comparison.csv", comparison)
        save_json(output / "evaluation.json", dict(comparison=comparison, intervals=intervals,
                                                   main_intervals=main_intervals))
        if (any(digest_file(Path(p)) != h for p, h in pins.items())
                or digest_file(declaration_path) != provenance["sha256"]
                or source_snapshot()[2] != provenance_source["files"]
                or digest_file(output / "frozen-protocol.json") != frozen_hash):
            raise ValueError("HeTCo sources changed during execution")
        if len(fits) != len(plan):
            raise ValueError("Incomplete frozen fit schedule")
        manifest.update(status="complete", finished_at=datetime.now(timezone.utc).isoformat(),
                        configuration_fits=len(fits), wall_seconds=perf_counter() - started,
                        artifact_hashes={p.relative_to(output).as_posix(): digest_file(p) for p in output.rglob("*")
                                         if p.is_file() and p.name != "manifest.json"})
        save_json(output / "manifest.json", manifest)
    except BaseException as exc:
        manifest.update(status="failed", failure_type=type(exc).__name__, configuration_fits=len(fits),
                        wall_seconds=perf_counter() - started)
        save_json(output / "manifest.json", manifest)
        raise
    return output
