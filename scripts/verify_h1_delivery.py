"""Verify the saved H1 experiment and export aggregate delivery tables; no fitting."""

import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path
import statistics
import tomllib

from reddit_sna.contracts import next_month
from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.research import EVENTS, KEY, score
from reddit_sna.models.hetco import tier1_decision

NAMES = {"attention": ("HeTCo_v4", "HeTCo_v5"),
         "mean": ("A7v4_mean_pool", "A7v5_mean_pool"),
         "LR_hier_community": ("LR_hier_community", "LR_hier_community_t1")}


def read(path):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def verify_inventory(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") not in ("complete", "complete_through_detection") or not manifest.get("artifact_hashes"):
        raise ValueError(f"Incomplete run: {directory}")
    for name, expected in manifest["artifact_hashes"].items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or digest_file(path) != expected:
            raise ValueError(f"Payload changed: {name}")
    return manifest


def verify(run, declaration_path):
    run = Path(run).resolve()
    manifest = verify_inventory(run)
    for name, expected in manifest["source_manifests"].items():
        if digest_file(Path(name)) != expected:
            raise ValueError("Source manifest changed")
        verify_inventory(Path(name).parent)
    research = next(Path(p).parent for p in manifest["source_manifests"] if Path(p).parent.parent.name == "research")
    verify_inventory(research)
    protocol = json.loads((research / "protocol.json").read_text(encoding="utf-8"))
    declaration_path = Path(declaration_path)
    declaration = tomllib.loads(declaration_path.read_text(encoding="utf-8"))
    provenance = dict(sha256=digest_file(declaration_path))
    if provenance["sha256"] != manifest["declaration"]["sha256"]:
        raise ValueError("Declaration differs from saved fit")
    if any(m >= protocol["test_start"] for m in declaration["selection_months"]):
        raise ValueError("Selection overlaps main evaluation")
    measured_fits = None
    if "frozen_protocol_sha256" in manifest:
        frozen_path = run / "frozen-protocol.json"
        if digest_file(frozen_path) != manifest["frozen_protocol_sha256"]:
            raise ValueError("Frozen protocol changed")
        frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
        if frozen["declaration"] != declaration or frozen["research_protocol"] != protocol:
            raise ValueError("Frozen configuration differs from declared inputs")
        fits = json.loads((run / "fits.json").read_text(encoding="utf-8"))
        fields = ("phase", "boundary", "seed", "family")
        if ([{k: r[k] for k in fields} for r in fits] != frozen["fit_plan"]
                or len(fits) != manifest["maximum_configuration_fits"]
                or len(fits) != manifest["configuration_fits"]
                or any(r["latest_train_label"] >= r["boundary"] for r in fits)):
            raise ValueError("Observed fits violate frozen budget or causal cutoff")
        measured_fits = len(fits)
        for name, expected in manifest["source"]["files"].items():
            if digest_file(run / "provenance/source" / name) != expected:
                raise ValueError("Archived pre-fit source changed")
    rows = read(run / "predictions.csv")
    groups = defaultdict(dict)
    truth = {}
    for row in rows:
        key = tuple(row[k] for k in KEY)
        unit = row["window"], row["model"], int(row["seed"])
        if key in groups[unit] or row["label_month"] != next_month(row["feature_month"]):
            raise ValueError("Duplicate key or invalid target month")
        if key in truth and truth[key] != row["y_true"]:
            raise ValueError("Truth differs across models/seeds/windows")
        truth[key] = row["y_true"]
        groups[unit][key] = row
    models = [name for pair in NAMES.values() for name in pair]
    expected = {(w, m, s) for w in ("main", "rolling") for m in models for s in protocol["seeds"]}
    if set(groups) != expected:
        raise ValueError("Incomplete model/seed/window schedule")
    samples = read(research / "samples.csv")
    for window in ("main", "rolling"):
        keys = {tuple(r[k] for k in KEY) for r in samples
                if (r["label_month"] >= protocol["test_start"] if window == "main"
                    else r["label_month"] in protocol["rolling_months"])}
        for unit, values in groups.items():
            if unit[0] == window and (set(values) != keys or any(
                    r["label"] != values[tuple(r[k] for k in KEY)]["y_true"]
                    for r in samples if tuple(r[k] for k in KEY) in keys)):
                raise ValueError("Predictions differ from declared sample inventory")
        for seed in protocol["seeds"]:
            for base, changed in NAMES.values():
                for key, a in groups[(window, base, seed)].items():
                    b = groups[(window, changed, seed)][key]
                    if a["p_dissolve"] != b["p_dissolve"]:
                        raise ValueError("Ablation probabilities differ between paired decisions")
                    probability = float(a["p_dissolve"])
                    if not math.isfinite(probability) or not 0 <= probability <= 1:
                        raise ValueError("Invalid dissolve probability")
                    family = next(f for f, pair in NAMES.items() if pair[0] == base)
                    threshold = manifest["selected"][family]
                    if all(f"p_{e}" in a for e in EVENTS):
                        probabilities = [float(a[f"p_{e}"]) for e in EVENTS]
                        if (any(not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities)
                                or not math.isclose(sum(probabilities), 1, abs_tol=1e-8)
                                or any(a[f"p_{e}"] != b[f"p_{e}"] for e in EVENTS)):
                            raise ValueError("Invalid or unmatched full-event probabilities")
                        rule = "argmax" if threshold == "argmax" else float(threshold)
                        if (tier1_decision([probabilities])[0] != a["y_pred"]
                                or tier1_decision([probabilities], rule)[0] != b["y_pred"]):
                            raise ValueError("Decision does not match saved full probabilities")
                    if threshold == "argmax":
                        if a["y_pred"] != b["y_pred"]:
                            raise ValueError("Unchanged argmax rule changed predictions")
                    elif ((b["y_pred"] == "dissolve") != (probability >= float(threshold))
                          or (a["y_pred"] != "dissolve" and b["y_pred"] != "dissolve"
                              and a["y_pred"] != b["y_pred"])):
                        raise ValueError("Ablation changes more than the tier-1 decision")
    reference = Path(manifest["refit_matches_reference"]["run"])
    verify_inventory(reference)
    stored = {(r["window"], r["model"], int(r["seed"]), *(r[k] for k in KEY)): r
              for r in read(reference / "predictions.csv")}
    matched = 0
    for r in rows:
        if r["model"] in ("HeTCo_v4", "A7v4_mean_pool"):
            a = stored[(r["window"], r["model"], int(r["seed"]), *(r[k] for k in KEY))]
            if a["y_true"] != r["y_true"] or a["y_pred"] != r["y_pred"]:
                raise ValueError("Argmax refit differs from archived predictions")
            matched += 1
    selection = read(run / "selection.csv")
    for family in NAMES:
        candidates = [r for r in selection if r["family"] == family]
        if ([r["threshold"] for r in candidates] != list(map(str, declaration["thresholds"]))
                or any(r["origins"].split() != declaration["selection_months"] for r in candidates)):
            raise ValueError("Selection grid or origins changed")
        if not all(math.isfinite(float(r["mean_macro_f1_six"])) for r in candidates):
            raise ValueError("Nonfinite selection score")
        chosen = max(candidates, key=lambda r: float(r["mean_macro_f1_six"]))["threshold"]
        if chosen != manifest["selected"][family]:
            raise ValueError("Selected threshold violates declared tie break")
    aggregate, classes = [], []
    comparison = {(r["window"], r["model"]): r for r in read(run / "comparison.csv")}
    for window in ("main", "rolling"):
        for model in models:
            values = [score(list(groups[(window, model, s)].values())) for s in protocol["seeds"]]
            mean = statistics.mean(v["macro_f1_six"] for v in values)
            if not math.isclose(mean, float(comparison[(window, model)]["mean_macro_f1_six"]), abs_tol=1e-12):
                raise ValueError("Stored score differs from prediction recomputation")
            missed, false, wrong = [], [], []
            for seed in protocol["seeds"]:
                predictions = list(groups[(window, model, seed)].values())
                missed.append(sum(r["y_true"] != "dissolve" and r["y_pred"] == "dissolve" for r in predictions))
                false.append(sum(r["y_true"] == "dissolve" and r["y_pred"] != "dissolve" for r in predictions))
                wrong.append(sum(r["y_true"] != "dissolve" and r["y_pred"] != "dissolve"
                                 and r["y_true"] != r["y_pred"] for r in predictions))
            aggregate.append(dict(window=window, model=model, n_per_seed=values[0]["n"],
                                  macro_f1=mean, seed_sd=statistics.stdev(v["macro_f1_six"] for v in values),
                                  missed_events=statistics.mean(missed), false_events=statistics.mean(false),
                                  wrong_event_type=statistics.mean(wrong)))
            for event in values[0]["per_class"]:
                classes.append(dict(window=window, model=model, event=event,
                    support_per_seed=values[0]["per_class"][event]["support"],
                    f1=statistics.mean(v["per_class"][event]["f1"] for v in values),
                    recall=statistics.mean(v["per_class"][event]["recall"] for v in values)))
    return aggregate, classes, dict(status="verified", run=str(run),
        prediction_rows=len(rows), archived_predictions_matched=matched,
        declaration_sha256=provenance["sha256"], selected=manifest["selected"],
        scheduled_selection_fits=len(NAMES)*len(protocol["seeds"])*len(declaration["selection_months"]),
        scheduled_evaluation_fits=len(NAMES)*len(protocol["seeds"])*(1+len(protocol["rolling_months"])),
        thresholds_per_family=len(declaration["thresholds"]), unseen=False,
        measured_configuration_fits=measured_fits,
        run_wall_seconds=manifest.get("wall_seconds"),
        source_snapshot_verified=measured_fits is not None,
        decision="H1 not supported; v4 retained; v5 reported as ablation",
        scope="2015 inspected pilot; not the group's full-study reference",
        payload_sha256=manifest["artifact_hashes"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path("artifacts/hetco/hetco-v5-001"))
    parser.add_argument("--declaration", type=Path, default=Path("configs/hetco_threshold.toml"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compare-run", type=Path, help="Require every prediction and selected threshold to reproduce an earlier run")
    args = parser.parse_args()
    aggregate, classes, audit = verify(args.run, args.declaration)
    if args.compare_run is not None:
        verify_inventory(args.compare_run)
        key = ("window", "model", "seed", *KEY)
        old_rows = read(args.compare_run / "predictions.csv")
        new_rows = read(args.run / "predictions.csv")
        old = {tuple(r[k] for k in key): r for r in old_rows}
        new = {tuple(r[k] for k in key): r for r in new_rows}
        previous = json.loads((args.compare_run / "manifest.json").read_text(encoding="utf-8"))
        if (len(old) != len(old_rows) or set(old) != set(new)
                or any((old[k]["y_true"], old[k]["y_pred"]) != (new[k]["y_true"], new[k]["y_pred"]) for k in old)
                or previous["selected"] != audit["selected"]):
            raise ValueError("Replay differs from earlier selected thresholds or keyed predictions")
        maximum_probability_difference = max(abs(float(old[k]["p_dissolve"])-float(new[k]["p_dissolve"])) for k in old)
        if not math.isfinite(maximum_probability_difference) or maximum_probability_difference > 1e-12:
            raise ValueError("Replay probabilities differ beyond 1e-12 absolute tolerance")
        audit["reproduces_run"] = str(args.compare_run)
        audit["reproduced_prediction_rows"] = len(old)
        audit["maximum_replay_dissolve_probability_difference"] = maximum_probability_difference
    args.output.mkdir(parents=True, exist_ok=False)
    contrasts = []
    for window in ("main", "rolling"):
        values = {r["model"]: r for r in aggregate if r["window"] == window}
        for family, (base, changed) in NAMES.items():
            contrasts.append(dict(window=window, family=family, primary=base, ablation=changed,
                primary_macro_f1=values[base]["macro_f1"], ablation_macro_f1=values[changed]["macro_f1"],
                delta=values[changed]["macro_f1"]-values[base]["macro_f1"]))
    for name, rows in (("ablation.csv", aggregate), ("per-class.csv", classes), ("contrasts.csv", contrasts)):
        with (args.output / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    evaluation = json.loads((args.run / "evaluation.json").read_text(encoding="utf-8"))
    intervals = [dict(scope=scope, **row) for scope, field in
                 (("main_community", "main_intervals"), ("rolling_month_blocks", "intervals"))
                 for row in evaluation[field]]
    (args.output / "saved-intervals.json").write_text(json.dumps(intervals, indent=2)+"\n", encoding="utf-8")
    if (args.run / "fits.json").is_file():
        fits = json.loads((args.run / "fits.json").read_text(encoding="utf-8"))
        with (args.output / "fit-log.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(fits[0]))
            writer.writeheader()
            writer.writerows(fits)
    (args.output / "verification.json").write_text(json.dumps(audit, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in audit.items() if k != "payload_sha256"}, indent=2))


if __name__ == "__main__":
    main()
