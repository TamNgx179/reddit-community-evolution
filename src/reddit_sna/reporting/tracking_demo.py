"""Read, validate and present the two saved tracking routes; never tune a tracker."""
import csv
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
from statistics import mean

from reddit_sna.evaluation.tracking import evaluate_events
from reddit_sna.reporting.synthetic_handoff import SCENARIOS, _path
from reddit_sna.reporting.tracking_outputs import INPUT_PINS, LABELS, TRACKER_CONFIG, _write_csv, _write_json


def _read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f"invalid CSV: {path}")
    return rows


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(path):
    return sha256(path.read_bytes()).hexdigest()


def read_tracking_run(directory, *, split, expected_input_sha256=None):
    """Verify complete inventory, fixed protocol, predictions and reported scores."""
    root = Path(directory).resolve()
    files = _json(root / "manifest.json")["files"]
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != root / "manifest.json"}
    _require(set(files) == actual, "tracking output inventory mismatch")
    for name, digest in files.items():
        _require(_sha(_path(root, name)) == digest, f"tracking output hash mismatch: {name}")
    meta = _json(root / "metadata.json")
    _require(meta["status"] == "complete" and meta["schema_version"] == 1
             and meta["artifact_type"] == "synthetic-tracking-replay", "incomplete tracking run")
    expected_pin = INPUT_PINS[split] if expected_input_sha256 is None else expected_input_sha256
    _require(meta["split"] == split and meta["input_manifest_sha256"] == expected_pin
             and meta["detector_seed"] == 0, "tracking input split/pin/seed mismatch")
    _require(_json(root / "tracker-config.json") == TRACKER_CONFIG
             and _sha(root / "tracker-config.json") == meta["tracker_config_sha256"], "tracking config mismatch")
    prefix, seeds = ("dev", (11, 12, 13)) if split == "development" else ("eval", (101, 102, 103))
    expected = {f"{prefix}-{case}-easy-g{seed}" for case in SCENARIOS for seed in seeds}
    _require(meta["datasets"] == 18 and set(meta["summaries"]) == expected
             and {p.name for p in (root / "datasets").iterdir()} == expected, "tracking dataset schedule mismatch")
    records, dataset_scores = [], []
    for dataset, summary in sorted(meta["summaries"].items()):
        truth_predictions = _read_csv(root / "datasets" / dataset / "truth_tracking/event_predictions.csv")
        truth = {r["source_community_id"]: r["truth_event"] for r in truth_predictions}
        _require(len(truth) == len(truth_predictions), "duplicate truth source")
        for route in ("truth_tracking", "detector_tracking"):
            path = root / "datasets" / dataset / route
            predictions = _read_csv(path / "event_predictions.csv")
            _require({r["source_community_id"]: r["truth_event"] for r in predictions} == truth
                     and len(predictions) == len(truth), "prediction sources/truth labels differ")
            scored = evaluate_events(
                [{"source_community_id": r["source_community_id"], "event": r["truth_event"]} for r in predictions],
                [{"source_community_id": r["source_community_id"], "event": r["predicted_event"]} for r in predictions])
            metrics = _read_csv(path / "metrics.csv")
            _require(len(metrics) == 7 and {r["event"] for r in metrics} == {*LABELS, "macro_f1"}, "invalid event metric rows")
            for label in LABELS:
                row = next(r for r in metrics if r["event"] == label)
                _require(all(isclose(float(row[k]), v, abs_tol=1e-12) for k, v in scored["metrics"][label].items()), "recorded event metrics differ")
            _require(isclose(float(next(r for r in metrics if r["event"] == "macro_f1")["f1"]), scored["macro_f1"], abs_tol=1e-12), "recorded macro-F1 differs")
            columns = (*LABELS, *(("__unmatched__",) if route == "detector_tracking" else ()))
            matrix = _read_csv(path / "confusion_matrix.csv")
            _require(len(matrix) == 6 and [r["truth_event"] for r in matrix] == list(LABELS)
                     and all(tuple(row) == ("truth_event", *columns) for row in matrix), "confusion schema mismatch")
            _require(all(int(row[col]) == scored["confusion_matrix"][row["truth_event"]][col]
                         for row in matrix for col in columns), "recorded confusion counts differ")
            reference = summary["truth_reference"] if route == "truth_tracking" else summary["detector_reference"]
            events, links = _read_csv(path / "events.csv"), _read_csv(path / "links.csv")
            _require(all(row["reference_id"] == reference and row["source_month"] == "2020-01"
                         and row["target_month"] == "2020-02" for row in [*events, *links]), "event/link reference or month mismatch")
            if route == "truth_tracking":
                _require(all(r["truth_event"] == r["predicted_event"] for r in predictions), "truth route is not exact")
                _require({r["source_community_id"]: r["event"] for r in events} == truth, "truth event output differs")
            else:
                mapping = _read_csv(path / "source_mapping.csv")
                _require(len({r["truth_community_id"] for r in mapping}) == len(mapping)
                         == len({r["detector_community_id"] for r in mapping}), "mapping is not one-to-one")
                by_detector = {r["source_community_id"]: r["event"] for r in events}
                mapped = {r["truth_community_id"]: r["detector_community_id"] for r in mapping}
                _require(all(r["predicted_event"] == by_detector.get(mapped.get(r["source_community_id"]), "__unmatched__")
                             for r in predictions), "projected event differs from mapping")
                diagnostics = _json(path / "mapping_diagnostics.json")
                _require(set(diagnostics["unmatched_truth"]) == set(truth) - set(mapped)
                         and set(diagnostics["extra_detector"]) == set(by_detector) - set(mapped.values()), "mapping diagnostics differ")
                _require(len(diagnostics["extra_detector"]) == summary["extra_detector"]
                         and len(diagnostics["unmatched_truth"]) == summary["unmatched_truth"], "mapping summary differs")
            diagnostics = _json(path / "tracker_diagnostics.json")
            _require(diagnostics["link_count"] == len(links) and diagnostics["source_count"] == len(events), "tracker diagnostics differ")
            key = "truth_macro_f1" if route == "truth_tracking" else "detector_macro_f1"
            _require(isclose(summary[key], scored["macro_f1"], abs_tol=1e-12), "dataset summary differs")
            dataset_scores.append({"split": split, "dataset_id": dataset, "route": route, "macro_f1": scored["macro_f1"]})
            for row in predictions:
                records.append({"split": split, "route": route, "dataset_id": dataset,
                                "truth_reference": summary["truth_reference"], "detector_reference": summary["detector_reference"],
                                "source_month": "2020-01", "target_month": "2020-02", **row})
    return {"directory": str(root), "manifest_sha256": _sha(root / "manifest.json"),
            "metadata": meta, "records": records, "dataset_scores": dataset_scores}


def pool_predictions(records):
    """Score qualified source keys; preserve missing predictions and six labels."""
    keys = [(r["dataset_id"], r["truth_reference"], r["source_month"], r["source_community_id"], r["target_month"]) for r in records]
    _require(len(set(keys)) == len(keys), "duplicate qualified tracking sample")
    # JSON encodes the tuple without delimiter collisions.
    return evaluate_events(
        [{"source_community_id": json.dumps(k), "event": r["truth_event"]} for k, r in zip(keys, records)],
        [{"source_community_id": json.dumps(k), "event": r["predicted_event"]} for k, r in zip(keys, records)])


def load_tracking_demo(development, evaluation, *, input_pins=None):
    runs = {split: read_tracking_run(path, split=split, expected_input_sha256=(input_pins or {}).get(split)) for split, path in
            (("development", development), ("evaluation", evaluation))}
    summaries, per_class, predictions, errors, matrices = [], [], [], [], {}
    for split, run in runs.items():
        for route in ("truth_tracking", "detector_tracking"):
            records = [r for r in run["records"] if r["route"] == route]
            result = pool_predictions(records)
            _require(result["support"] == 39 and [result["metrics"][label]["support"] for label in LABELS] == [21, 3, 3, 6, 3, 3], "pooled event support mismatch")
            rows = run["metadata"]["summaries"].values()
            summaries.append({"split": split, "route": route, "support": 39,
                              "mean_dataset_macro_f1": mean(r["macro_f1"] for r in run["dataset_scores"] if r["route"] == route),
                              "pooled_macro_f1": result["macro_f1"],
                              "correct": sum(r["truth_event"] == r["predicted_event"] for r in records),
                              "matched_coverage": result["matched_support"] / 39,
                              "extra_detector": sum(r["extra_detector"] for r in rows) if route == "detector_tracking" else 0})
            per_class.extend({"split": split, "route": route, "event": label, **values} for label, values in result["metrics"].items())
            predictions.extend(records)
            errors.extend(r for r in records if r["truth_event"] != r["predicted_event"])
            matrices[split + "/" + route] = result["confusion_matrix"]
    return {"runs": runs, "summary": summaries, "per_class": per_class, "predictions": predictions, "errors": errors, "matrices": matrices}


def build_tracking_figures(demo):
    import matplotlib.pyplot as plt
    import numpy as np
    figures = {}
    for split in ("development", "evaluation"):
        fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
        for ax, route in zip(axes, ("truth_tracking", "detector_tracking")):
            columns = (*LABELS, *(("__unmatched__",) if route == "detector_tracking" else ()))
            counts = demo["matrices"][split + "/" + route]
            matrix = np.array([[counts[label][column] for column in columns] for label in LABELS])
            ax.imshow(matrix, cmap="Blues", vmin=0)
            ax.set_xticks(range(len(columns)), columns, rotation=45, ha="right")
            ax.set_yticks(range(6), LABELS)
            for i in range(6):
                for j in range(len(columns)):
                    ax.text(j, i, str(matrix[i, j]), ha="center", va="center", color="white" if matrix[i, j] > 10 else "black")
            score = next(r["pooled_macro_f1"] for r in demo["summary"] if r["split"] == split and r["route"] == route)
            ax.set_title(f"{split} / {route}\npooled macro-F1={score:.4f}")
            ax.set_xlabel("Predicted event")
            ax.set_ylabel("Truth event")
        figures[split + "-tracking-confusion"] = fig
    return figures


def export_tracking_demo(demo, figures, destination):
    """Save tables/figures in a fresh directory with a hash inventory written last."""
    root = Path(destination).resolve()
    _require(set(figures) == {"development-tracking-confusion", "evaluation-tracking-confusion"}, "missing tracking figures")
    for run in demo["runs"].values():
        source = Path(run["directory"])
        _require(not root.is_relative_to(source) and not source.is_relative_to(root), "tracking export overlaps input")
        _require(_sha(source / "manifest.json") == run["manifest_sha256"], "tracking source manifest changed")
        for name, digest in _json(source / "manifest.json")["files"].items():
            _require(_sha(_path(source, name)) == digest, "tracking source bytes changed")
    root.mkdir(parents=True)
    for name, rows in (("tracking-summary.csv", demo["summary"]), ("tracking-per-class.csv", demo["per_class"]),
                       ("tracking-predictions.csv", demo["predictions"]), ("tracking-errors.csv", demo["errors"])):
        _write_csv(root / name, tuple(rows[0]) if rows else tuple(demo["predictions"][0]), rows)
    for key, matrix in demo["matrices"].items():
        columns = (*LABELS, *(("__unmatched__",) if key.endswith("detector_tracking") else ()))
        _write_csv(root / (key.replace("/", "-") + ".csv"), ("truth_event", *columns),
                   [{"truth_event": label, **matrix[label]} for label in LABELS])
    for name, figure in figures.items():
        figure.savefig(root / (name + ".png"), dpi=140)
        figure.savefig(root / (name + ".svg"))
    metadata = {"status": "complete", "scope": "Verified synthetic tracking replay; see each source run for historical/current execution provenance",
                "partner_acceptance": "not_verified", "figure_count": 2, "prediction_rows": len(demo["predictions"]),
                "source_manifests": {s: run["manifest_sha256"] for s, run in demo["runs"].items()},
                "files": {p.name: {"sha256": _sha(p), "bytes": p.stat().st_size} for p in sorted(root.iterdir())}}
    _write_json(root / "metadata.json", metadata)
    return metadata
