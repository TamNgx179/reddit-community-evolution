"""Detect every configured development dataset from an existing graph/truth run.

This command completes detection only: no generation, AMI, tracking or evaluation
split. Use a new run ID every time. A failed run keeps completed/partial outputs.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from reddit_sna.artifacts import create_run_directory
from reddit_sna.benchmarks.config import dataset_schedule, load_benchmark_config
from reddit_sna.config import RunConfig, load_config, validate_destination
from reddit_sna.contracts import PipelineName
from reddit_sna.detection.leiden import dependencies
from reddit_sna.pipelines.detection_tracking import export_synthetic_detection


def run_development_detection(config: RunConfig, source_run: Path, benchmark_path: Path) -> Path:
    source_run, benchmark_path = source_run.resolve(), benchmark_path.resolve()
    benchmark_bytes = benchmark_path.read_bytes()
    benchmark = load_benchmark_config(benchmark_path)
    detector = benchmark["detector"]
    if (config.pipeline != PipelineName.DETECTION_TRACKING or config.input_kind != "synthetic"
            or config.seed != detector["canonical_seed"]
            or detector != {"seeds": [0, 1, 2], "gamma": 1.0, "canonical_seed": 0}):
        raise ValueError("development detection requires the synthetic namespace and canonical detector seed 0")
    destination = validate_destination(config)
    if destination.is_relative_to(source_run) or source_run.is_relative_to(destination):
        raise ValueError("detection run must not overlap its source run")
    manifest_bytes = (source_run / "manifest.json").read_bytes()
    source_manifest = json.loads(manifest_bytes.decode("utf-8"))
    schedule = dataset_schedule(benchmark, "development")
    expected = [item["dataset_id"] for item in schedule]
    if (not isinstance(source_manifest, dict) or source_manifest.get("status") != "complete"
            or source_manifest.get("artifact_type") != "synthetic-graph-truth-run"
            or source_manifest.get("split") != "development" or source_manifest.get("datasets") != expected
            or source_manifest.get("completed_stages") != ["generation", "truth"]
            or not isinstance(source_manifest.get("files"), dict)):
        raise ValueError("source must be a complete graph/truth run matching the full development schedule")
    if {p.name for p in (source_run / "datasets").iterdir() if p.is_dir()} != set(expected):
        raise ValueError("source dataset directories must match the development schedule exactly")
    # Only graph/config/metadata are detector inputs; do not read truth CSVs.
    source_files = {"manifest.json": {"sha256": sha256(manifest_bytes).hexdigest()}}
    for dataset_id in expected:
        names = ["metadata.json", "benchmark-config.json"]
        names += [f"snapshots/{month}/{name}.csv" for month in benchmark["months"] for name in ("R", "nodes")]
        for name in names:
            relative = f"datasets/{dataset_id}/{name}"
            path = (source_run / relative).resolve()
            if not path.is_relative_to(source_run):
                raise ValueError("source graph path escapes its run")
            digest = sha256(path.read_bytes()).hexdigest()
            info = source_manifest["files"].get(relative)
            if not isinstance(info, dict) or digest != info.get("sha256"):
                raise ValueError(f"source run SHA-256 mismatch: {relative}")
            source_files[relative] = {"sha256": digest}
    dependencies()
    root = Path(__file__).resolve().parents[1]
    source_code = {name: sha256((root / name).read_bytes()).hexdigest() for name in (
        "scripts/run_development_detection.py", "src/reddit_sna/pipelines/detection_tracking.py",
        "src/reddit_sna/detection/leiden.py",
    )}
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=root,
                           capture_output=True, text=True)
    run = create_run_directory(config)
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        artifact_type="synthetic-detection-run", scope="development-detection", split="development",
        completed_stages=[], datasets=[], expected_datasets=expected, current_dataset=None,
        source_run=str(source_run), source_files=source_files, source_code=source_code,
        source_revision=revision.stdout.strip() if revision.returncode == 0 else None,
        working_tree=dirty.stdout.splitlines() if dirty.returncode == 0 else None,
        run_config_sha256=sha256(config.source.read_bytes()).hexdigest(),
        benchmark_config={"source": str(benchmark_path), "path": "benchmark-config.json",
                          "sha256": sha256(benchmark_bytes).hexdigest()},
        configured_seed_role="canonical detector seed; full schedule read from benchmark JSON",
        selection={"generator_seeds": benchmark["generator"]["seeds"]["development"], "mode": "all-development-seeds"},
        detector=detector, expected_counts={"datasets": len(expected), "snapshots": len(expected) * len(benchmark["months"]),
                                           "memberships": len(expected) * len(benchmark["months"]) * len(detector["seeds"])},
    )
    started = perf_counter()
    try:
        with (run / "benchmark-config.json").open("xb") as handle:
            handle.write(benchmark_bytes)
        (run / "datasets").mkdir()
        for dataset_id in expected:
            manifest["current_dataset"] = dataset_id
            export_synthetic_detection(source_run / "datasets" / dataset_id, run / "datasets" / dataset_id,
                                       benchmark_config=benchmark_path)
            manifest["datasets"].append(dataset_id)
        if any(sha256((source_run / name).read_bytes()).hexdigest() != info["sha256"]
               for name, info in source_files.items()):
            raise ValueError("source run changed during detection")
        if benchmark_path.read_bytes() != benchmark_bytes:
            raise ValueError("benchmark config changed during detection")
        manifest.update(status="complete", completed_stages=["detection"], current_dataset=None,
                        files={p.relative_to(run).as_posix(): {"sha256": sha256(p.read_bytes()).hexdigest()}
                               for p in sorted(run.rglob("*")) if p.is_file() and p != manifest_path})
    except Exception as exc:
        manifest.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        manifest.update(finished_at=datetime.now(timezone.utc).isoformat(), detection_wall_seconds=perf_counter() - started)
        # Rewrite only the started manifest created by this invocation.
        with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(manifest, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n")
    return run


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/detection_development.toml"))
    parser.add_argument("--benchmark-config", type=Path, default=Path("configs/benchmark_week1.json"))
    args = parser.parse_args(argv)
    try:
        run = run_development_detection(load_config(args.config, run_id=args.run_id), args.source_run, args.benchmark_config)
    except (OSError, ValueError) as exc:
        print(f"development detection failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"scope": "development-detection", "status": "complete", "run_directory": str(run)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
