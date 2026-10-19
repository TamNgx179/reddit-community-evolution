"""Freeze a verified full development protocol without executing held-out data."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

from reddit_sna.artifacts import (
    capture_run_provenance, create_run_directory, run_file_inventory, save_run_manifest,
)
from reddit_sna.benchmarks.config import dataset_schedule
from reddit_sna.benchmarks.protocol import BenchmarkProtocol, _exact, _json_file, load_benchmark_protocol
from reddit_sna.config import ConfigError, RunConfig, load_config, validate_destination
from reddit_sna.contracts import PipelineName


@dataclass(frozen=True)
class BenchmarkFreeze:
    directory: Path
    manifest: dict
    manifest_sha256: str
    protocol: BenchmarkProtocol


def _require(condition, message):
    if not condition:
        raise ConfigError(message)


def _complete_manifest(directory, schema, artifact_type):
    _require(not any((directory / name).exists() for name in ("failure.json", "manifest.pending.json")),
             "failure/pending marker prevents consuming this run")
    content, manifest = _json_file(directory / "manifest.json")
    _require(isinstance(manifest, dict) and type(manifest.get("schema_version")) is int
             and manifest["schema_version"] == schema and manifest.get("artifact_type") == artifact_type
             and manifest.get("status") == "complete", "a complete supported manifest is required")
    _exact(run_file_inventory(directory), manifest.get("files"), "output inventory")
    return content, manifest


def _runtime_matches(source, environment):
    _require(isinstance(source, dict) and isinstance(source.get("files"), dict)
             and isinstance(environment, dict), "source/environment metadata is incomplete")
    current_source, current_environment, _ = capture_run_provenance()
    _exact(source.get("files"), current_source["files"], "runtime source hashes")
    for key in ("python_version", "python_implementation", "packages"):
        _exact(environment.get(key), current_environment[key], "runtime environment " + key)
    return current_source, current_environment


def _development_record(manifest, plan):
    _require(isinstance(manifest, dict), "development manifest must be an object")
    ids = [row["dataset_id"] for row in dataset_schedule(plan.benchmark, "development")]
    counts = plan.protocol["expected_counts"]["development"]
    _require(manifest.get("status") == "complete" and type(manifest.get("schema_version")) is int
             and manifest["schema_version"] == 2 and manifest.get("artifact_type") == "synthetic-detection-evaluation-run"
             and manifest.get("scope") == "development-detection-evaluation" and manifest.get("split") == "development"
             and manifest.get("tracking_status") == "not_implemented" and manifest.get("freeze_record_created") is False,
             "a development detection-evaluation run is required")
    _exact(manifest.get("selection"), {"mode": "full-development", "dataset_ids": ids}, "full development selection")
    _exact(manifest.get("expected_counts"), counts, "development expected counts")
    _exact(manifest.get("actual_counts"), counts, "development actual counts")
    _exact(manifest.get("progress_counts"), {name + "_datasets": len(ids) for name in ("generated", "detected", "evaluated")},
           "development progress counts")
    _exact(manifest.get("completed_stages"), ["generation", "truth", "detection", "evaluation"], "development completed stages")
    _require(manifest.get("current_stage") is None and manifest.get("current_dataset") is None
             and all(manifest.get("stages", {}).get(stage, {}).get("status") == "complete"
                     for stage in ("configuration", "generation", "detection", "evaluation")), "development stages are incomplete")
    records = manifest.get("dataset_records", {})
    _require(set(records) == set(ids) and all(records[name].get(stage, {}).get("status") == "complete"
             for name in ids for stage in ("generation", "detection", "evaluation")), "development dataset records are incomplete")
    _require(manifest.get("integrity", {}).get("status") == "verified"
             and manifest["integrity"].get("source_unchanged") is True, "development integrity is not verified")
    return ids


def _holdout_metadata(namespace):
    """Inspect artifact identity only, never held-out graph/truth/prediction rows."""
    found = []
    for path in sorted(namespace.rglob("metadata.json")):
        _, metadata = _json_file(path)
        if (isinstance(metadata, dict) and metadata.get("split") == "evaluation"
                and metadata.get("artifact_type") in ("synthetic-graph-truth", "synthetic-detection")):
            found.append(path.relative_to(namespace).as_posix())
    return found


def create_benchmark_freeze(config: RunConfig, *, development_run: Path, protocol: Path) -> Path:
    """Create a new, separate freeze run after checking full development evidence.

    Keep the completed development manifest immutable. Freeze all package Python
    source/pyproject bytes and supported Python/package versions. A later external
    orchestration script may use these modules unchanged and record its own source.
    This operation never generates or scores evaluation datasets.
    """
    _require(config.pipeline == PipelineName.DETECTION_TRACKING and config.input_kind == "synthetic"
             and config.input_path is None and type(config.seed) is int and config.seed == 0,
             "freeze requires detection-tracking, synthetic input and canonical seed 0")
    destination = validate_destination(config)
    development_run = development_run.resolve()
    _require(development_run.is_relative_to((config.project_root / "artifacts").resolve())
             and not destination.is_relative_to(development_run) and not development_run.is_relative_to(destination),
             "development and freeze must be separate runs inside project artifacts")
    plan = load_benchmark_protocol(protocol)
    dev_bytes, dev = _complete_manifest(development_run, 2, "synthetic-detection-evaluation-run")
    ids = _development_record(dev, plan)
    _runtime_matches(dev["source"], dev["environment"])
    source, environment = dev["source"], dev["environment"]
    config_sources = (("protocol", plan.protocol_path, plan.protocol_sha256),
                      ("benchmark", plan.benchmark_path, plan.benchmark_sha256),
                      ("run_config", config.source, sha256(config.source.read_bytes()).hexdigest()))
    for role, path, digest in config_sources:
        info = dev.get("config_inputs", {}).get(role, {})
        _require(info.get("sha256") == digest and dev["files"].get(info.get("archive"), {}).get("sha256") == digest,
                 "development configuration differs: " + role)
    observed_holdout = _holdout_metadata((config.project_root / "artifacts/detection-tracking").resolve())
    _require(not observed_holdout, "held-out output metadata already exists; cannot claim a pre-evaluation freeze")
    # Only copy verified files already covered by the immutable development inventory.
    names = [name for name in dev["files"] if name.startswith(("config/", "provenance/", "evaluation/"))]
    blobs = {name: (development_run / name).read_bytes() for name in names}
    _require(all(sha256(data).hexdigest() == dev["files"][name]["sha256"] for name, data in blobs.items()),
             "development files changed before freeze")
    run = create_run_directory(config)
    manifest = json.loads((run / "manifest.json").read_bytes())
    manifest.update(schema_version=1, artifact_type="synthetic-benchmark-freeze", scope="benchmark-protocol-freeze",
        freeze_record_created=False, evaluation_executed=False, tracking_status="not_implemented", frozen_at=None,
        source=source, environment=environment, changes_from_development=[],
        development={"run_id": development_run.name, "source_directory": str(development_run),
            "manifest": "development/manifest.json", "manifest_sha256": sha256(dev_bytes).hexdigest(),
            "dataset_ids": ids, "counts": dev["actual_counts"]},
        frozen_protocol={"archive": dev["config_inputs"]["protocol"]["archive"], "sha256": plan.protocol_sha256,
            "benchmark_sha256": plan.benchmark_sha256},
        schedules={split: list(dataset_schedule(plan.benchmark, split)) for split in ("development", "evaluation")},
        expected_counts=plan.protocol["expected_counts"],
        holdout_audit={"scope": "synthetic graph/detection metadata under project artifacts/detection-tracking",
            "observed_evaluation_metadata": observed_holdout}, files={})
    try:
        save_run_manifest(run, manifest)
        for name, data in blobs.items():
            target = run / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (run / "development").mkdir()
        (run / "development/manifest.json").write_bytes(dev_bytes)
        _require((development_run / "manifest.json").read_bytes() == dev_bytes
                 and run_file_inventory(development_run) == dev["files"], "development changed during freeze")
        _runtime_matches(source, environment)
        _require(all(sha256(path.read_bytes()).hexdigest() == digest for _, path, digest in config_sources),
                 "source configuration changed during freeze")
        _require(not _holdout_metadata((config.project_root / "artifacts/detection-tracking").resolve()),
                 "held-out output metadata appeared during freeze")
        manifest.update(status="complete", freeze_record_created=True, frozen_at=datetime.now(timezone.utc).isoformat(),
                        files=run_file_inventory(run))
        save_run_manifest(run, manifest)
    except BaseException as exc:
        manifest.update(status="failed", freeze_record_created=False, frozen_at=None,
                        error={"type": type(exc).__name__, "message": str(exc)})
        try:
            manifest["files"] = run_file_inventory(run)
            save_run_manifest(run, manifest)
        except Exception as publication_error:
            try:
                (run / "failure.json").write_text(json.dumps({**manifest, "publication_error": str(publication_error)},
                    ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            except OSError:
                pass
        raise
    return run


def load_benchmark_freeze(directory: Path) -> BenchmarkFreeze:
    """Verify the frozen bundle and current source/versions; never execute a dataset.

    Read archive paths from the verified development mapping rather than opening
    absolute producer paths. Git HEAD may advance for docs/drivers while every
    frozen package source byte and supported runtime version must still match.
    """
    directory = directory.resolve()
    content, frozen = _complete_manifest(directory, 1, "synthetic-benchmark-freeze")
    _require(frozen.get("scope") == "benchmark-protocol-freeze" and frozen.get("freeze_record_created") is True
             and frozen.get("evaluation_executed") is False and frozen.get("tracking_status") == "not_implemented"
             and isinstance(frozen.get("frozen_at"), str), "a completed pre-evaluation freeze is required")
    _require(all(isinstance(frozen.get(key), dict) for key in ("development", "frozen_protocol", "source", "environment")),
             "freeze metadata is incomplete")
    relative = frozen.get("frozen_protocol", {}).get("archive")
    _require(isinstance(relative, str) and relative in frozen["files"], "frozen protocol archive is missing")
    plan = load_benchmark_protocol(directory / relative)
    _require(plan.protocol_sha256 == frozen["frozen_protocol"]["sha256"]
             and plan.benchmark_sha256 == frozen["frozen_protocol"]["benchmark_sha256"], "frozen protocol hashes differ")
    dev_bytes, dev = _json_file(directory / "development/manifest.json")
    _require(sha256(dev_bytes).hexdigest() == frozen["development"]["manifest_sha256"], "development manifest hash differs")
    ids = _development_record(dev, plan)
    expected_files = {name for name in dev["files"] if name.startswith(("config/", "provenance/", "evaluation/"))}
    _require(set(frozen["files"]) == expected_files | {"development/manifest.json"}, "frozen archive file set is incomplete")
    _exact(frozen["development"]["dataset_ids"], ids, "frozen development selection")
    _exact(frozen["development"]["counts"], dev["actual_counts"], "frozen development counts")
    _exact(frozen.get("expected_counts"), plan.protocol["expected_counts"], "frozen counts")
    _exact(frozen.get("schedules"), {split: list(dataset_schedule(plan.benchmark, split))
                                    for split in ("development", "evaluation")}, "frozen schedules")
    _exact(frozen.get("changes_from_development"), [], "changes from development")
    for name, info in frozen["files"].items():
        if name != "development/manifest.json":
            _require(dev["files"].get(name) == info, "frozen file differs from development: " + name)
    _exact(frozen["source"]["files"], dev["source"]["files"], "frozen source hashes")
    _exact(frozen["environment"], dev["environment"], "frozen development environment")
    _exact(frozen.get("holdout_audit", {}).get("observed_evaluation_metadata"), [], "pre-freeze holdout audit")
    try:
        frozen_at = datetime.fromisoformat(frozen["frozen_at"])
        finished_at = datetime.fromisoformat(dev["finished_at"])
        _require(frozen_at.utcoffset() is not None and finished_at.utcoffset() is not None
                 and frozen_at >= finished_at, "freeze must be timestamped after development finished")
    except (TypeError, ValueError) as exc:
        raise ConfigError("invalid development/freeze chronology") from exc
    _runtime_matches(frozen["source"], frozen["environment"])
    return BenchmarkFreeze(directory, frozen, sha256(content).hexdigest(), plan)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="Freeze a full development run; no held-out execution")
    create.add_argument("--config", type=Path, default=Path("configs/detection_development.toml"))
    create.add_argument("--protocol", type=Path, default=Path("configs/benchmark_week1_protocol.json"))
    create.add_argument("--development-run", type=Path, required=True)
    create.add_argument("--run-id", required=True)
    verify = commands.add_parser("verify", help="Read and validate a freeze without executing data")
    verify.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            output = create_benchmark_freeze(load_config(args.config, run_id=args.run_id),
                                             development_run=args.development_run, protocol=args.protocol)
            result = load_benchmark_freeze(output)
        else:
            result = load_benchmark_freeze(args.directory)
    except (OSError, ValueError) as exc:
        print(f"benchmark freeze failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "verified", "scope": "benchmark-protocol-freeze", "directory": str(result.directory),
        "manifest_sha256": result.manifest_sha256, "frozen_at": result.manifest["frozen_at"],
        "freeze_record_created": True, "evaluation_executed": False, "expected_counts": result.manifest["expected_counts"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
