"""Run the entire held-out schedule through the unchanged, frozen package.

This external driver was explicitly allowed by PHUC-005-T05. It verifies the
freeze before any data access and archives its own source separately. It never
selects seeds by score, modifies the freeze or overwrites an existing run.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from importlib import import_module
import json
from pathlib import Path
import sys
from time import perf_counter

from reddit_sna.artifacts import RunRecorder, capture_run_provenance, create_run_directory
from reddit_sna.benchmarks.freeze import load_benchmark_freeze
from reddit_sna.benchmarks.io import export_graph_dataset
from reddit_sna.config import ConfigError, RunConfig, load_config, validate_destination
from reddit_sna.contracts import PipelineName
from reddit_sna.detection.leiden import dependencies
from reddit_sna.evaluation.detection import export_detection_evaluation
from reddit_sna.pipelines.detection_tracking import export_synthetic_detection


def _require(condition, message):
    if not condition:
        raise ConfigError(message)


def _driver_source():
    path = Path(__file__).resolve()
    return path, path.read_bytes()


def _json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")


def run_frozen_evaluation(config: RunConfig, *, freeze: Path) -> Path:
    """Execute every frozen evaluation identity, retaining partial output on error."""
    started = perf_counter()
    _require(config.pipeline == PipelineName.DETECTION_TRACKING and config.input_kind == "synthetic"
             and config.input_path is None and type(config.seed) is int and config.seed == 0,
             "held-out evaluation requires detection-tracking, synthetic input and canonical seed 0")
    destination = validate_destination(config)
    frozen = load_benchmark_freeze(freeze)
    protected = (frozen.directory, Path(frozen.manifest["development"]["source_directory"]).resolve())
    _require(not any(destination.is_relative_to(path) or path.is_relative_to(destination) for path in protected),
             "evaluation output must not overlap freeze or development")
    _require(datetime.fromisoformat(frozen.manifest["frozen_at"]) <= datetime.now(timezone.utc),
             "evaluation cannot start before the freeze timestamp")
    selected = frozen.manifest["schedules"]["evaluation"]
    expected = {"datasets": len(selected), "snapshots": len(selected) * len(frozen.protocol.benchmark["months"]),
        "snapshot_detector_runs": len(selected) * len(frozen.protocol.benchmark["months"]) * len(frozen.protocol.benchmark["detector"]["seeds"])}
    _require(expected == frozen.manifest["expected_counts"]["evaluation"], "evaluation schedule counts differ")
    config_bytes = config.source.read_bytes()
    _require(sha256(config_bytes).hexdigest() == frozen.manifest["files"]["config/run-config.toml"]["sha256"],
             "runtime TOML differs from the frozen run configuration")
    freeze_bytes = {name: (frozen.directory / name).read_bytes() for name in ("manifest.json", *frozen.manifest["files"])}
    _require(sha256(freeze_bytes["manifest.json"]).hexdigest() == frozen.manifest_sha256
             and all(sha256(freeze_bytes[name]).hexdigest() == info["sha256"] for name, info in frozen.manifest["files"].items()),
             "freeze changed during preflight")
    dependencies()
    import_module("sklearn.metrics")
    source, environment, source_bytes = capture_run_provenance()
    _require(source["files"] == frozen.manifest["source"]["files"], "package source differs from freeze")
    driver_path, driver_bytes = _driver_source()
    run = create_run_directory(config)
    manifest = json.loads((run / "manifest.json").read_bytes())
    manifest.update(schema_version=2, artifact_type="synthetic-frozen-evaluation-run", scope="heldout-detection-evaluation",
        split="evaluation", source=source, environment=environment, freeze_record_created=False, evaluation_executed=False,
        tracking_status="not_implemented", expected_counts=expected,
        selection={"mode": "full-evaluation", "dataset_ids": [item["dataset_id"] for item in selected]},
        completed_stages=[], current_stage="configuration", current_dataset=None, generated_datasets=[], detected_datasets=[],
        preflight_wall_seconds=perf_counter() - started,
        preflight_scope="freeze/config/source/backend checks and input snapshots before run reservation",
        freeze_reference={"source": str(frozen.directory), "archive": "freeze", "manifest_sha256": frozen.manifest_sha256,
            "frozen_at": frozen.manifest["frozen_at"], "source_revision": frozen.manifest["source"]["git"]["revision"]},
        driver={"source": str(driver_path), "archive": "provenance/driver/" + driver_path.name,
            "sha256": sha256(driver_bytes).hexdigest(), "role": "orchestration outside frozen package"},
        config_inputs={
            "protocol": {"source": str(frozen.protocol.protocol_path), "archive": "config/protocol/" + frozen.protocol.protocol_path.name,
                         "sha256": frozen.protocol.protocol_sha256},
            "benchmark": {"source": str(frozen.protocol.benchmark_path), "archive": "config/protocol/" + frozen.protocol.benchmark_path.name,
                          "sha256": frozen.protocol.benchmark_sha256},
            "run_config": {"source": str(config.source), "archive": "config/run-config.toml", "sha256": sha256(config_bytes).hexdigest()}},
        dataset_records={item["dataset_id"]: {**item, **{stage: {"status": "pending", "wall_seconds": None}
            for stage in ("generation", "detection", "evaluation")}} for item in selected})
    recorder = RunRecorder(run, manifest)
    try:
        _require(datetime.fromisoformat(manifest["created_at"]) >= datetime.fromisoformat(frozen.manifest["frozen_at"]),
                 "run reservation predates freeze")
        with recorder.stage("configuration"):
            for name, data in freeze_bytes.items():
                target = run / "freeze" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            archived = load_benchmark_freeze(run / "freeze")
            for role in ("protocol", "benchmark"):
                info = manifest["config_inputs"][role]
                target = run / info["archive"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(freeze_bytes[frozen.manifest["frozen_protocol"]["archive"]] if role == "protocol"
                                   else archived.protocol.benchmark_path.read_bytes())
            (run / "config/run-config.toml").write_bytes(config_bytes)
            _json(run / "config/resolved-run-config.json", config.to_dict())
            manifest["resolved_config"] = {"archive": "config/resolved-run-config.json",
                "sha256": sha256((run / "config/resolved-run-config.json").read_bytes()).hexdigest()}
            for name, data in source_bytes.items():
                target = run / source["archive_root"] / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            target = run / manifest["driver"]["archive"]
            target.parent.mkdir(parents=True)
            target.write_bytes(driver_bytes)
            _json(run / "provenance/source.json", source)
            _json(run / "provenance/environment.json", environment)
            source_root, detected_root = run / "inputs/source", run / "inputs/detected"
            source_root.mkdir(parents=True)
            detected_root.mkdir()
        manifest.update(evaluation_executed=True, heldout_access_started_at=datetime.now(timezone.utc).isoformat())
        with recorder.stage("generation"):
            for item in selected:
                dataset = item["dataset_id"]
                with recorder.dataset("generation", dataset) as record:
                    export_graph_dataset(source_root / dataset, benchmark=archived.protocol.benchmark,
                        scenario=item["scenario"], generator_seed=item["generator_seed"], split="evaluation")
                    record["metadata"] = f"inputs/source/{dataset}/metadata.json"
                    manifest["generated_datasets"].append(dataset)
        with recorder.stage("detection"):
            for item in selected:
                dataset = item["dataset_id"]
                with recorder.dataset("detection", dataset) as record:
                    export_synthetic_detection(source_root / dataset, detected_root / dataset,
                        benchmark_config=archived.protocol.benchmark_path)
                    record["metadata"] = f"inputs/detected/{dataset}/metadata.json"
                    manifest["detected_datasets"].append(dataset)
        with recorder.stage("evaluation"):
            report = export_detection_evaluation([(source_root / item["dataset_id"], detected_root / item["dataset_id"])
                                                  for item in selected], run / "evaluation")
            actual = {"datasets": report["dataset_count"],
                "snapshots": report["metric_rows"] // len(archived.protocol.benchmark["detector"]["seeds"]),
                "snapshot_detector_runs": report["metric_rows"]}
            _require(actual == expected, "held-out report counts differ from the frozen schedule")
            _require(config.source.read_bytes() == config_bytes, "source TOML changed during evaluation")
            _require(sha256(_driver_source()[1]).hexdigest() == manifest["driver"]["sha256"], "driver changed during evaluation")
            _require(load_benchmark_freeze(frozen.directory).manifest_sha256 == frozen.manifest_sha256,
                     "freeze changed during evaluation")
            manifest.update(actual_counts=actual, evaluation_directory="evaluation")
        recorder.complete()
    except BaseException as exc:
        recorder.fail(exc)
        raise
    return run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/detection_development.toml"))
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    try:
        output = run_frozen_evaluation(load_config(args.config, run_id=args.run_id), freeze=args.freeze)
    except (OSError, ValueError, ImportError) as exc:
        print(f"frozen evaluation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "complete", "scope": "heldout-detection-evaluation", "run_directory": str(output),
        "evaluation_executed": True, "freeze_record_created": False, "tracking_status": "not_implemented"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
