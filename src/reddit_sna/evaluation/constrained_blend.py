"""Select a constrained probability blend on development months and replay it."""

import argparse
import csv
import json
import math
from pathlib import Path

from threadpoolctl import threadpool_limits

from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.diagnostics import paired_tables
from reddit_sna.evaluation.research import EVENTS, KEY, score
from reddit_sna.models.activity_forecast import fit_activity_model, predict_activity_model

LR = "hier_lr_dynamic"
HGB = "hier_hgb_dynamic"
BLEND = "development_selected_blend"
WEIGHTS = (0.0, 0.25, 0.5, 0.75, 1.0)


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def verify_inputs(root, pins):
    for name, expected in pins.items():
        if digest_file(root / name) != expected:
            raise ValueError(f"Input checksum mismatch: {name}")


def _prediction(probabilities):
    return EVENTS[max(range(len(EVENTS)), key=probabilities.__getitem__)]


def _index(rows):
    indexed = {}
    for row in rows:
        key = (row["seed"], *(row[field] for field in KEY))
        probabilities = row["probabilities"]
        if key in indexed or any(value is None or value == "" for value in key):
            raise ValueError(f"Duplicate or incomplete prediction key: {key}")
        if (
            len(probabilities) != len(EVENTS)
            or any(not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities)
            or not math.isclose(sum(probabilities), 1, abs_tol=1e-8)
        ):
            raise ValueError(f"Invalid event probabilities: {key}")
        if row["y_true"] not in EVENTS or row["y_pred"] != _prediction(probabilities):
            raise ValueError(f"Invalid event label or argmax: {key}")
        indexed[key] = row
    return indexed


def match_predictions(lr, hgb):
    """Validate aligned six-class forecasts before comparing decisions."""
    left, right = _index(lr), _index(hgb)
    if not left or left.keys() != right.keys():
        raise ValueError("LR and HGB prediction keys must match exactly")
    pairs = [(left[key], right[key]) for key in sorted(left)]
    if any(a["y_true"] != b["y_true"] for a, b in pairs):
        raise ValueError("LR and HGB reference labels disagree")
    return pairs


def blend(pairs, weight):
    if weight not in WEIGHTS:
        raise ValueError("Weight is outside the declared candidate grid")
    rows = []
    for lr, hgb in pairs:
        probabilities = [
            (1 - weight) * a + weight * b
            for a, b in zip(lr["probabilities"], hgb["probabilities"], strict=True)
        ]
        fallback = int((weight < 1 and lr["fallback"]) or
                       (weight > 0 and hgb["fallback"]))
        rows.append(dict(lr, model=BLEND, y_pred=_prediction(probabilities),
                         probabilities=probabilities, fallback=fallback))
    return rows


def _measures(rows):
    summary = score(rows)
    return dict(
        n=summary["n"],
        macro_f1=summary["macro_f1_six"],
        grow_support=summary["per_class"]["grow"]["support"],
        merge_support=summary["per_class"]["merge"]["support"],
        grow_hits=sum(r["y_true"] == r["y_pred"] == "grow" for r in rows),
        merge_hits=sum(r["y_true"] == r["y_pred"] == "merge" for r in rows),
        false_alarms=sum(r["y_true"] == "dissolve" != r["y_pred"] for r in rows),
    )


def _by_seed(rows, seeds):
    if {row["seed"] for row in rows} != set(seeds):
        raise ValueError("Prediction seeds differ from the frozen protocol")
    return {seed: _measures([r for r in rows if r["seed"] == seed]) for seed in seeds}


def select_weight(pairs, seeds):
    """Require a strict per-seed improvement over both frozen endpoints."""
    trials = []
    reference = _by_seed([lr for lr, _ in pairs], seeds)
    comparator = _by_seed([hgb for _, hgb in pairs], seeds)
    for weight in WEIGHTS:
        metrics = _by_seed(blend(pairs, weight), seeds)
        eligible = 0 < weight < 1 and all(
            m["grow_support"] > 0
            and m["merge_support"] > 0
            and m["macro_f1"] > max(reference[s]["macro_f1"], comparator[s]["macro_f1"])
            and m["grow_hits"] >= reference[s]["grow_hits"]
            and m["merge_hits"] >= reference[s]["merge_hits"]
            and m["false_alarms"] <= reference[s]["false_alarms"]
            for s, m in metrics.items()
        )
        trials.append(dict(weight=weight, eligible=eligible, by_seed=metrics,
                           mean_macro_f1=sum(m["macro_f1"] for m in metrics.values()) / len(seeds)))
    selected = max((t for t in trials if t["eligible"]),
                   key=lambda t: (t["mean_macro_f1"], -t["weight"]), default=None)
    reason = "eligible_blend_selected"
    if selected is None:
        reason = ("missing_rare_class_support" if any(
            not m["grow_support"] or not m["merge_support"] for m in reference.values()
        ) else "no_blend_passed_development_constraints")
    return dict(weight=selected["weight"] if selected else 0.0, reason=reason, trials=trials)


def development_predictions(samples, definitions, protocol):
    start, cutoff = protocol["validation_start"], protocol["test_start"]
    if any(r["label_month"] >= cutoff for r in samples):
        raise ValueError("Development samples contain final-window labels")
    months = sorted({r["label_month"] for r in samples if r["label_month"] >= start})
    if not months:
        raise ValueError("No development validation origins")
    rows = {LR: [], HGB: []}
    fit_log = []
    for month in months:
        train = [r for r in samples if r["label_month"] < month]
        valid = [r for r in samples if r["label_month"] == month]
        if not train:
            raise ValueError(f"No earlier training labels for {month}")
        for model, output in rows.items():
            definition = definitions[model]
            for seed in protocol["seeds"]:
                fitted = fit_activity_model(train, definition["fields"], definition["settings"],
                                            definition["hierarchical"], seed)
                if fitted["latest_train_label"] >= month:
                    raise ValueError("Model fit reached the validation month")
                labels, probabilities, fallback = predict_activity_model(fitted, valid)
                fit_log.append(dict(model=model, seed=seed, validation_month=month,
                                    latest_train_label=fitted["latest_train_label"],
                                    train_support=fitted["support"], validation_n=len(valid)))
                for row, label, probs, flag in zip(valid, labels, probabilities, fallback, strict=True):
                    output.append(dict({field: row[field] for field in KEY}, seed=seed,
                                       model=model, window="final", y_true=row["label"],
                                       y_pred=label, probabilities=probs, fallback=flag))
    return match_predictions(rows[LR], rows[HGB]), fit_log


def replay(root, plan, weight):
    counts, intervals = [], []
    for cohort, item in plan["cohorts"].items():
        stages = root / item["root"] / "stages"
        features = _csv(stages / "evaluation-samples/attempt-001/features.csv")
        rows = [
            dict(row, seed=int(row["seed"]), window="final", fallback=int(row["fallback"]),
                 probabilities=json.loads(row["probabilities"]))
            for row in _csv(stages / "evaluation/attempt-001/predictions.csv")
            if row["model"] in (LR, HGB)
        ]
        pairs = match_predictions([r for r in rows if r["model"] == LR],
                                  [r for r in rows if r["model"] == HGB])
        rows.extend(blend(pairs, weight))
        for model in (LR, HGB, BLEND):
            counts.extend(dict(cohort=cohort, model=model, seed=seed, **m)
                          for seed, m in _by_seed([r for r in rows if r["model"] == model],
                                                  plan["seeds"]).items())
        spec = plan["bootstrap"]
        for block in (spec["block_length"], spec["sensitivity_block_length"]):
            _, comparison = paired_tables(rows, features, [(BLEND, LR), (BLEND, HGB)],
                                          draws=spec["draws"], block_length=block,
                                          bootstrap_seed=spec["seed"])
            intervals.extend(dict(cohort=cohort, **row) for row in comparison)
    return dict(counts=counts, intervals=intervals)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = _json(args.evidence / "manifest.json")["lr_hgb_cross_cohort"]
    verify_inputs(args.evidence, {"lr_hgb_cross_cohort_protocol.json": manifest["protocol_sha256"]})
    plan = _json(args.evidence / "lr_hgb_cross_cohort_protocol.json")
    if plan["models"] != [LR, HGB]:
        raise ValueError("Unexpected frozen model definitions")
    root = args.artifact_root
    primary = plan["cohorts"]["full-study"]
    verify_inputs(root, primary["pins"])
    study = root / primary["root"]
    protocol = _json(study / "protocol.json")
    if protocol["seeds"] != plan["seeds"]:
        raise ValueError("Development and replay seed declarations differ")
    freeze = _json(study / "freeze.json")
    samples = study / "stages/development-samples/attempt-001/samples.csv"
    selection = study / "stages/selection/attempt-001"
    verify_inputs(study, {samples.relative_to(study): freeze["development_samples_sha256"],
                          (selection / "complete.json").relative_to(study):
                          freeze["selection_manifest_sha256"]})
    verify_inputs(selection, {"selection.json": _json(selection / "complete.json")
                              ["artifact_hashes"]["selection.json"]})
    args.output.mkdir(parents=True, exist_ok=False)
    _write(args.output / "protocol.json", dict(
        scope=plan["scope"], weights=WEIGHTS, validation_start=protocol["validation_start"],
        test_start=protocol["test_start"], seeds=protocol["seeds"],
        selection="strict per-seed Macro-F1 gain over LR and HGB, no loss in grow/merge hits or rise in false alarms versus LR",
        development_samples_sha256=freeze["development_samples_sha256"],
        definition_manifest_sha256=freeze["selection_manifest_sha256"],
        replay_protocol_sha256=manifest["protocol_sha256"]))
    with threadpool_limits(limits=1):
        pairs, fit_log = development_predictions(_csv(samples), _json(selection / "selection.json")
                                                 ["definitions"], protocol)
    locked = dict(select_weight(pairs, protocol["seeds"]), fit_log=fit_log,
                  protocol_sha256=digest_file(args.output / "protocol.json"))
    selection_path = args.output / "selection.json"
    _write(selection_path, locked)
    verify_inputs(root, manifest["inputs"])
    for cohort in plan["cohorts"].values():
        verify_inputs(root, cohort["pins"])
    result = replay(root, plan, _json(selection_path)["weight"])
    _write(args.output / "replay.json", dict(result, selection_sha256=digest_file(selection_path)))
    print(f"{locked['reason']}: HGB weight {locked['weight']:.2f}")


if __name__ == "__main__":
    main()
