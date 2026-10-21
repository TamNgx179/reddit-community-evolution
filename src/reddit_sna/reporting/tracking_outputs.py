"""Write reproducible development artifacts for the Jaccard tracker."""

import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import re
from typing import Iterable, Mapping

from reddit_sna.evaluation.tracking import evaluate_events, project_detector_events
from reddit_sna.tracking.jaccard import track
from reddit_sna.tracking.membership import groups_by_month, read_memberships
from reddit_sna.reporting.synthetic_handoff import inspect_synthetic_handoff

EVENT_COLUMNS = (
    "reference_id",
    "source_month",
    "source_community_id",
    "target_month",
    "event",
)
LINK_COLUMNS = (
    "reference_id",
    "source_month",
    "source_community_id",
    "target_month",
    "target_community_id",
)
PREDICTION_COLUMNS = (
    "source_community_id",
    "truth_event",
    "predicted_event",
    "status",
)
MAPPING_COLUMNS = (
    "truth_community_id",
    "detector_community_id",
    "jaccard",
    "status",
)
LABELS = ("stable", "grow", "shrink", "merge", "split", "dissolve")
INPUT_PINS = {
    "development": "34364c98519e394af8541b9093a78899469239856f583d01608ec8848ade4e8e",
    "evaluation": "e305a6a0fe4d0068e50159f9078fe893de266d10d13ca9d5b18bd46df4aae16c",
}
SOURCE_RUNS = {"development": "phuc-005-t05-development-001", "evaluation": "phuc-005-t06-evaluation-001"}
TRACKER_CONFIG = {
    "jaccard_threshold": 0.30, "size_tolerance": 0.10, "detector_seed": 0,
    "precedence": ["dissolve", "split", "merge", "grow", "shrink", "stable"],
    "mapping": "source-month greedy one-to-one; score descending, truth ID then detector ID ascending; Jaccard >= 0.30",
    "labels": list(LABELS), "zero_division": 0,
    "truth_confusion_shape": [6, 6], "detector_confusion_shape": [6, 7],
    "upstream_revision": "57a39c67835e9a08efe0fe22eea99e5095b0c3d1",
    "scope": "Fixed PR12 algorithm replay. This file records this replay config, not a historical pre-evaluation freeze by Dang.",
}


def _write_csv(path: Path, columns: Iterable[str], rows: Iterable[Mapping[str, object]]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _event_rows(reference: str, events: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "reference_id": reference,
            "source_month": "2020-01",
            "source_community_id": row["source_community_id"],
            "target_month": "2020-02",
            "event": row["event"],
        }
        for row in events
    ]


def _link_rows(reference: str, links: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "reference_id": reference,
            "source_month": "2020-01",
            "source_community_id": row["source_community_id"],
            "target_month": "2020-02",
            "target_community_id": row["target_community_id"],
        }
        for row in links
    ]


def _write_evaluation(directory: Path, result: Mapping[str, object], *, allow_unmatched: bool = True) -> None:
    if not allow_unmatched and result["matched_support"] != result["support"]:
        raise ValueError("truth route must predict every source")
    _write_csv(directory / "event_predictions.csv", PREDICTION_COLUMNS, result["event_predictions"])
    metric_rows = [
        {"event": label, **values}
        for label, values in result["metrics"].items()
    ]
    metric_rows.append(
        {
            "event": "macro_f1",
            "precision": "",
            "recall": "",
            "f1": result["macro_f1"],
            "support": result["support"],
        }
    )
    _write_csv(directory / "metrics.csv", ("event", "precision", "recall", "f1", "support"), metric_rows)
    matrix = result["confusion_matrix"]
    matrix_rows = [
        {"truth_event": label, **matrix[label]}
        for label in LABELS
    ]
    _write_csv(
        directory / "confusion_matrix.csv",
        ("truth_event", *LABELS, *(("__unmatched__",) if allow_unmatched else ())),
        matrix_rows,
    )
    _write_json(
        directory / "diagnostics.json",
        {
            "support": result["support"],
            "matched_support": result["matched_support"],
            "matched_coverage": (
                result["matched_support"] / result["support"]
                if result["support"]
                else 0.0
            ),
            "unmatched_truth_sources": result["unmatched_truth_sources"],
            "extra_prediction_sources": result["extra_prediction_sources"],
            "macro_f1": result["macro_f1"],
        },
    )


def _read_truth_events(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _run_dataset(
    source_dataset: Path,
    detected_dataset: Path,
    output_dataset: Path,
) -> dict[str, object]:
    truth_dir = source_dataset / "truth"
    truth_rows = read_memberships(truth_dir / "membership.csv")
    truth_reference = truth_rows[0].reference_id
    truth_groups = groups_by_month(truth_rows, expected_reference=truth_reference)
    tracker_args = {"tau": TRACKER_CONFIG["jaccard_threshold"], "size_tolerance": TRACKER_CONFIG["size_tolerance"]}
    truth_result = track(truth_groups["2020-01"], truth_groups["2020-02"], **tracker_args)
    truth_events = _read_truth_events(truth_dir / "events.csv")
    truth_eval = evaluate_events(truth_events, truth_result["events"])

    truth_output = output_dataset / "truth_tracking"
    truth_output.mkdir(parents=True)
    _write_csv(truth_output / "events.csv", EVENT_COLUMNS, _event_rows(truth_reference, truth_result["events"]))
    _write_csv(truth_output / "links.csv", LINK_COLUMNS, _link_rows(truth_reference, truth_result["links"]))
    _write_evaluation(truth_output, truth_eval, allow_unmatched=False)
    _write_json(truth_output / "tracker_diagnostics.json", truth_result["diagnostics"])
    if _read_truth_events(truth_dir / "events.csv") != _read_truth_events(truth_output / "events.csv"):
        raise ValueError("truth tracker event rows differ from the declared truth")
    def canonical(rows):
        return sorted(tuple(sorted(row.items())) for row in rows)
    if canonical(_read_truth_events(truth_dir / "links.csv")) != canonical(_read_truth_events(truth_output / "links.csv")):
        raise ValueError("truth tracker links differ from the declared truth")

    detector_dir = detected_dataset / "memberships"
    detector_paths = [
        detector_dir / month / "membership-seed0.csv"
        for month in ("2020-01", "2020-02")
    ]
    detector_rows = []
    for path in detector_paths:
        detector_rows.extend(read_memberships(path))
    detector_reference = detector_rows[0].reference_id
    detector_groups = groups_by_month(detector_rows, expected_reference=detector_reference)
    detector_result = track(detector_groups["2020-01"], detector_groups["2020-02"], **tracker_args)
    projected = project_detector_events(
        truth_groups["2020-01"],
        detector_groups["2020-01"],
        detector_result["events"],
        tau=TRACKER_CONFIG["jaccard_threshold"],
    )
    detector_eval = evaluate_events(truth_events, projected["event_predictions"])
    detector_output = output_dataset / "detector_tracking"
    detector_output.mkdir()
    _write_csv(detector_output / "events.csv", EVENT_COLUMNS, _event_rows(detector_reference, detector_result["events"]))
    _write_csv(detector_output / "links.csv", LINK_COLUMNS, _link_rows(detector_reference, detector_result["links"]))
    _write_csv(detector_output / "source_mapping.csv", MAPPING_COLUMNS, projected["mapping"])
    _write_evaluation(detector_output, detector_eval)
    _write_json(detector_output / "tracker_diagnostics.json", detector_result["diagnostics"])
    _write_json(
        detector_output / "mapping_diagnostics.json",
        {
            "unmatched_truth": projected["unmatched_truth"],
            "extra_detector": projected["extra_detector"],
            "missing_detector_events": projected["missing_detector_events"],
            "tau": projected["tau"],
        },
    )
    return {
        "truth_reference": truth_reference,
        "detector_reference": detector_reference,
        "truth_macro_f1": truth_eval["macro_f1"],
        "detector_macro_f1": detector_eval["macro_f1"],
        "detector_matched_coverage": detector_eval["matched_support"] / detector_eval["support"],
        "unmatched_truth": len(projected["unmatched_truth"]),
        "extra_detector": len(projected["extra_detector"]),
    }


def _run_split(
    handoff_root: Path,
    output_root: Path,
    *,
    run_id: str,
    split: str,
    source_run: str,
    input_manifest_sha256: str,
    current_source: Path | None = None,
) -> Path:
    """Create a fresh tracking run without modifying handoff inputs."""
    if split not in {"development", "evaluation"}:
        raise ValueError("split must be development or evaluation")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id):
        raise ValueError("run_id must be a portable single directory name")
    handoff_root, output_root = Path(handoff_root).resolve(), Path(output_root).resolve()
    destination = output_root / run_id
    if destination.exists():
        raise FileExistsError(destination)
    if destination.is_relative_to(handoff_root) or handoff_root.is_relative_to(destination):
        raise ValueError("tracking output must not overlap the handoff inputs")
    if current_source is None and (input_manifest_sha256 != INPUT_PINS[split] or source_run != SOURCE_RUNS[split]):
        raise ValueError("input pin or source run does not match the fixed week-one split")
    input_run = (handoff_root / "runs" / split) if current_source is None else Path(current_source).resolve()
    if destination.is_relative_to(input_run) or input_run.is_relative_to(destination):
        raise ValueError("tracking output must not overlap the source run")
    inventory = inspect_synthetic_handoff(input_run, expected_manifest_sha256=input_manifest_sha256)
    if inventory["split"] != split or inventory["counts"]["datasets"] != 18:
        raise ValueError("tracking requires the full fixed split")
    source_root = input_run / "inputs" / "source"
    detected_root = input_run / "inputs" / "detected"
    datasets = sorted(path for path in source_root.iterdir() if path.is_dir())
    if len(datasets) != 18:
        raise ValueError(f"expected 18 development datasets, found {len(datasets)}")
    destination.mkdir(parents=True)
    started = datetime.now(timezone.utc).isoformat()
    _write_json(destination / "tracker-config.json", TRACKER_CONFIG)
    package = Path(__file__).resolve().parents[1]
    provenance = {"python": platform.python_version(), "platform": platform.platform(),
                  "implementation_files": {name: _digest(package / name) for name in (
                      "tracking/membership.py", "tracking/jaccard.py", "evaluation/tracking.py",
                      "reporting/tracking_outputs.py", "contracts.py", "benchmarks/io.py", "reporting/synthetic_handoff.py")},
                  "started_at_utc": started, "origin": "Phuc integration replay of Dang PR12; original Dang output folders not received",
                  "historical_dang_freeze": "not_verified", "new_independent_holdout_claim": False}
    if current_source is not None:
        provenance["origin"] = "Current-source descriptive rerun; not a historical Dang freeze or new unseen test"
    _write_json(destination / "provenance.json", provenance)
    summaries = {}
    for dataset in datasets:
        summaries[dataset.name] = _run_dataset(
            dataset,
            detected_root / dataset.name,
            destination / "datasets" / dataset.name,
        )
    metadata = {
        "schema_version": 1,
        "artifact_type": "synthetic-tracking-replay",
        "status": "complete",
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "origin": provenance["origin"],
        "replay_mode": "legacy_pinned" if current_source is None else "current_source",
        "tracker_config_sha256": _digest(destination / "tracker-config.json"),
        "run_id": run_id,
        "split": split,
        "source_run": source_run,
        "input_manifest_sha256": input_manifest_sha256,
        "detector_seed": 0,
        "jaccard_threshold": 0.30,
        "size_tolerance": 0.10,
        "datasets": 18,
        "summaries": summaries,
    }
    if current_source is not None:
        # Archive the recipe whose bytes were already checked by the source
        # consumer. New schedules must never borrow the historical easy IDs.
        source_manifest = json.loads((input_run / "manifest.json").read_text(encoding="utf-8"))
        recipe_info = source_manifest["config_inputs"]["benchmark"]
        recipe_path = (input_run / recipe_info["archive"]).resolve()
        if not recipe_path.is_relative_to(input_run) or _digest(recipe_path) != recipe_info["sha256"]:
            raise ValueError("Tracking source recipe binding mismatch")
        (destination / "source-recipe.json").write_bytes(recipe_path.read_bytes())
        metadata["source_recipe_sha256"] = recipe_info["sha256"]
    _write_json(destination / "metadata.json", metadata)
    files = {}
    for path in sorted(destination.rglob("*")):
        if path.is_file():
            files[path.relative_to(destination).as_posix()] = _digest(path)
    _write_json(destination / "manifest.json", {"files": files})
    return destination



def run_split(handoff_root: Path, output_root: Path, *, run_id: str, split: str,
              source_run: str, input_manifest_sha256: str) -> Path:
    """Replay the original historical handoff; its trusted pins remain unchanged."""
    return _run_split(handoff_root, output_root, run_id=run_id, split=split,
                      source_run=source_run, input_manifest_sha256=input_manifest_sha256)


def run_current_split(source: Path, output_root: Path, *, run_id: str, split: str,
                      source_manifest_sha256: str) -> Path:
    """Track a new full source run with an explicit caller-pinned manifest.

    This is a descriptive new execution. It does not certify an unseen period or
    replace the fixed pins used by run_split for the historical T02 archive.
    """
    return _run_split(source, output_root, run_id=run_id, split=split,
                      source_run=Path(source).name,
                      input_manifest_sha256=source_manifest_sha256, current_source=source)


def run_development(
    handoff_root: Path,
    output_root: Path,
    *,
    run_id: str,
    input_manifest_sha256: str,
) -> Path:
    """Create a fresh development tracking run."""
    return run_split(
        handoff_root,
        output_root,
        run_id=run_id,
        split="development",
        source_run="phuc-005-t05-development-001",
        input_manifest_sha256=input_manifest_sha256,
    )
