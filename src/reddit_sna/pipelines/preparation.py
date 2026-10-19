"""Independently runnable Reddit data-to-membership preparation, not full forecasting."""

from datetime import datetime, timezone
import hashlib
from importlib.metadata import distributions
import json
from pathlib import Path
import subprocess
import time

from reddit_sna.artifacts import create_run_directory
from reddit_sna.config import RunConfig
from reddit_sna.contracts import PipelineName
from reddit_sna.data.archive import CORPORA, audit_archives, digest_file, selected_archives
from reddit_sna.data.normalize import month_boundary, normalize_archives
from reddit_sna.detection.leiden import dependencies, detect_snapshots
from reddit_sna.graphs.snapshots import build_snapshots
from reddit_sna.graphs.provenance import LEGACY_GRAPH_PROTOCOL, snapshot_inventory

STAGES = ("audit", "normalize", "snapshots", "detect", "all")


def save_json(path: Path, value) -> None:
    """Serialize aggregate metadata in UTF-8; never pass raw user/text payloads here."""
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _source(config: RunConfig, source: Path | None, stage: str) -> Path | None:
    """Verify a completed source and every declared hash before reserving downstream output."""
    if stage in {"snapshots", "detect"}:
        if source is None:
            raise ValueError("--source-run is required for snapshots/detect")
        source = source.resolve()
        if not source.is_relative_to((config.project_root / "artifacts").resolve()):
            raise ValueError("source run must stay inside project artifacts")
        manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("status") not in {"complete", "complete_through_detection"}:
            raise ValueError("source run is incomplete or failed")
        hashes = manifest.get("artifact_hashes", {})
        required = "normalized.sqlite" if stage == "snapshots" else "snapshots.json"
        if required not in hashes:
            raise ValueError("source run lacks required verified stage artifact")
        for relative, expected in hashes.items():
            path = (source / relative).resolve()
            if not path.is_relative_to(source) or digest_file(path) != expected:
                raise ValueError("source run artifact hash mismatch")
        return source
    if source is not None:
        raise ValueError("--source-run is only supported for snapshots/detect")
    return None


def _detect_info(source: Path) -> tuple[dict, dict]:
    """Bind snapshot metadata to actual directory months, file contents and graph semantics."""
    info = json.loads((source / "snapshots.json").read_text(encoding="utf-8"))
    if (not isinstance(info, dict) or not isinstance(info.get("months"), list)
            or not isinstance(info.get("identity_scope"), str) or not info["identity_scope"]
            or any(not isinstance(m, dict) or not isinstance(m.get("month"), str) for m in info["months"])):
        raise ValueError("invalid snapshot summary schema")
    months = [m["month"] for m in info["months"]]
    inventory = snapshot_inventory(source / "snapshots",
                                   protocol=info.get("graph_protocol", LEGACY_GRAPH_PROTOCOL),
                                   expected_months=months)
    for field in ("graph_reference", "snapshot_cohort_sha256", "start_month", "end_month_exclusive", "actual_months", "month_graphs"):
        if field in info and info[field] != inventory[field]:
            raise ValueError("snapshot metadata does not match verified graph content/period")
    return info, inventory


def run_preparation(config: RunConfig, *, stage="all", start=None, end=None,
            corpora=CORPORA, source_run: Path | None = None) -> Path:
    """Run one preparation stage or raw-to-membership with CLI-equivalent rules.

    Validate dependencies, cutoff and source integrity before creating a fresh
    run. Downstream stages inherit source periods; detection rejects subsets.
    Return the output directory and record completion/failure and artifact hashes.
    This pipeline stops before tracking, features and forecasting evaluation."""
    if config.pipeline != PipelineName.CORE or stage not in STAGES:
        raise ValueError("Preparation stages require a core config and a supported stage")
    # Original core config remains untouched; same safe run-directory policy.
    source = _source(config, source_run, stage)
    graph_info, inventory = _detect_info(source) if stage == "detect" else (None, None)
    if inventory:
        if ((start is not None and start != inventory["start_month"])
                or (end is not None and end != inventory["end_month_exclusive"])):
            raise ValueError("detect interval must match source snapshots; build a new snapshot run for a subset")
        start, end = inventory["start_month"], inventory["end_month_exclusive"]
    else:
        inherited = json.loads((source / "manifest.json").read_text(encoding="utf-8")) if source else {}
        start = start if start is not None else inherited.get("start_month", "2015-01")
        end = end if end is not None else inherited.get("end_month_exclusive", "2015-04")
    if month_boundary(start) >= month_boundary(end) or start < "2015-01" or end > "2017-07":
        raise ValueError("pilot must be a nonempty interval inside official train")
    paths = selected_archives(config.input_path, tuple(corpora)) if stage in {"audit", "normalize", "all"} else []
    if stage in {"detect", "all"}:
        dependencies()  # Fail before reserving output if dependency installation is missing.
    output = create_run_directory(config)
    started = time.perf_counter()
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({"stage": stage, "start_month": start, "end_month_exclusive": end,
                     "source_run": str(source) if source else None,
                     "source_manifest_sha256": digest_file(source / "manifest.json") if source else None,
                     "config_sha256": hashlib.sha256(config.source.read_bytes()).hexdigest(),
                     "completed_stages": [], "forecast_status": "not_run_by_preparation"})
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config.project_root,
                              capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=config.project_root,
                           capture_output=True, text=True)
    manifest["git"] = {"revision": revision.stdout.strip() if revision.returncode == 0 else None,
                       "tracked_dirty": bool(dirty.stdout.strip()),
                       "source_hashes": {str(p.relative_to(config.project_root)): digest_file(p)
                                         for p in sorted((config.project_root / "src" / "reddit_sna").rglob("*.py"))}}
    manifest["dependencies"] = {d.metadata["Name"]: d.version for d in distributions() if d.metadata["Name"]}
    save_json(manifest_path, manifest)
    try:
        if stage in {"audit", "normalize", "all"}:
            audit = audit_archives(paths)
            save_json(output / "corpus_manifest.json", audit)
            manifest["completed_stages"].append("audit")
        if stage in {"normalize", "all"}:
            summary = normalize_archives(paths, output / "normalized.sqlite", end)
            save_json(output / "normalization.json", summary)
            manifest["completed_stages"].append("normalize")
            # Detect concurrent input mutations even when CRC remains valid.
            for path, record in zip(paths, audit["archives"]):
                if digest_file(path) != record["sha256"]:
                    raise ValueError("raw archive changed after audit")
        if stage in {"snapshots", "all"}:
            database = (source or output) / "normalized.sqlite"
            declared = tuple(path.name.removesuffix(".corpus.zip") for path in paths) if paths else None
            if source and (source / "normalization.json").is_file():
                normalization = json.loads((source / "normalization.json").read_text(encoding="utf-8"))
                declared = tuple(c["corpus"] for c in normalization["corpora"])
            summary = build_snapshots(database, output / "snapshots", start, end, corpora=declared)
            save_json(output / "snapshots.json", summary)
            manifest.update({k: summary[k] for k in ("actual_months", "graph_protocol", "graph_reference", "identity_scope")})
            manifest["completed_stages"].append("snapshots")
        if stage in {"detect", "all"}:
            graph_source = source or output
            if graph_info is None:
                graph_info, inventory = _detect_info(graph_source)
            summary = detect_snapshots(graph_source / "snapshots", output / "memberships", graph_info["identity_scope"],
                                       graph_protocol=inventory["graph_protocol"], expected_months=inventory["actual_months"])
            save_json(output / "detection.json", summary)
            manifest.update({k: summary[k] for k in ("actual_months", "graph_protocol", "graph_reference")})
            manifest["identity_scope"] = graph_info["identity_scope"]
            manifest["completed_stages"].append("detect")
        manifest["status"] = "complete_through_detection" if stage == "all" else "complete"
        return output
    except BaseException as exc:
        manifest["status"] = "failed"
        # Only log type; messages may include payload data from third-party libraries.
        manifest["failure_type"] = type(exc).__name__
        raise
    finally:
        manifest["wall_seconds"] = time.perf_counter() - started
        manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
        manifest["peak_memory_mb"] = None
        manifest["resource_note"] = "peak memory not measured; wall time measured"
        manifest["artifact_hashes"] = {
            str(p.relative_to(output)): digest_file(p) for p in sorted(output.rglob("*"))
            if p.is_file() and p != manifest_path
        }
        save_json(manifest_path, manifest)
