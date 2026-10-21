"""Reserve isolated run directories and record provenance for future real runs."""

from datetime import datetime, timezone
from contextlib import contextmanager
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter

from reddit_sna.config import ConfigError, RunConfig, validate_destination


def create_run_directory(config: RunConfig) -> Path:
    """Create a new run exclusively. Never resume or overwrite an existing run.

    Real pipeline implementations should call this only after checking that all
    required stages and dependencies are ready. The scaffold CLI does not call it.
    A started manifest is provenance, not evidence of successful evaluation.
    """
    destination = validate_destination(config)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Recheck resolved paths after creating parents, before the exclusive mkdir.
    destination = validate_destination(config)
    try:
        destination.mkdir(exist_ok=False)
    except FileExistsError as exc:
        raise ConfigError(f"run already exists: {destination}") from exc
    manifest = {
        "status": "started",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "package_version": version("reddit-community-evolution"),
        "python_version": platform.python_version(),
        "config": config.to_dict(),
    }
    with (destination / "manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return destination


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def save_run_manifest(run: Path, manifest: dict) -> None:
    """Atomically publish the manifest of a newly reserved, caller-owned run."""
    pending = run / "manifest.pending.json"
    pending.write_bytes(_json_bytes(manifest))
    pending.replace(run / "manifest.json")


def source_snapshot():
    """Read the installed package source, rather than assuming config.project_root contains it."""
    package = Path(__file__).resolve().parent
    blobs = {"reddit_sna/" + p.relative_to(package).as_posix(): p.read_bytes()
             for p in sorted(package.rglob("*.py")) if p.is_file()}
    project_file = package.parent.parent / "pyproject.toml"
    if project_file.is_file():
        blobs["pyproject.toml"] = project_file.read_bytes()
    hashes = {name: sha256(data).hexdigest() for name, data in blobs.items()}
    return package, blobs, hashes


def capture_run_provenance():
    """Capture source bytes, Git state and an explicit allowlist of runtime metadata."""
    package, blobs, hashes = source_snapshot()
    git = {"status": "unavailable", "repository": None, "revision": None, "branch": None, "working_tree": None}
    try:
        results = {}
        for key, args in (("repository", ["rev-parse", "--show-toplevel"]), ("revision", ["rev-parse", "HEAD"]),
                          ("branch", ["branch", "--show-current"]), ("working_tree", ["status", "--porcelain=v1", "--untracked-files=all"])):
            result = subprocess.run(["git", "-C", str(package), *args], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                break
            results[key] = result.stdout.strip()
        else:
            git.update(status="available", **results)
    except (OSError, subprocess.TimeoutExpired):
        pass
    packages = {}
    for name in ("reddit-community-evolution", "igraph", "leidenalg", "scikit-learn", "numpy", "scipy"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    environment = {"python_version": platform.python_version(), "python_implementation": platform.python_implementation(),
                   "python_executable": sys.executable, "platform": platform.platform(), "packages": packages,
                   "python_hash_seed": os.environ.get("PYTHONHASHSEED")}
    source = {"package_directory": str(package), "archive_root": "provenance/source", "files": hashes, "git": git}
    return source, environment, blobs


def run_file_inventory(run: Path) -> dict:
    """Hash output bytes, excluding the mutable root manifest and its pending replacement."""
    root, result = run.resolve(), {}
    for path in sorted(run.rglob("*")):
        if not path.is_file():
            continue
        name = path.relative_to(run).as_posix()
        if name in ("manifest.json", "manifest.pending.json"):
            continue
        if not path.resolve().is_relative_to(root):
            raise ValueError("run inventory file escapes the run directory")
        data = path.read_bytes()
        result[name] = {"sha256": sha256(data).hexdigest(), "bytes": len(data)}
    return result


class RunRecorder:
    """Record benchmark stages and immutable outputs without resuming an old run."""
    def __init__(self, run: Path, manifest: dict):
        self.run, self.manifest = run, manifest
        self.started, self.phase = perf_counter(), "configuration"
        self.sealed = {}
        manifest.update(files={}, integrity={"status": "pending"}, stages={
            name: {"status": "pending", "started_at": None, "finished_at": None, "wall_seconds": None}
            for name in ("configuration", "generation", "detection", "evaluation")},
            timing={"run_wall_seconds": None, "verification_wall_seconds": None, "peak_memory_bytes": None,
                    "run_scope": "from recorder initialization through final verification; excludes final manifest publication",
                    "stage_scope": "wrapper wall time including dataset checkpoints and end-of-stage integrity checks; excludes boundary checkpoint writes",
                    "dataset_scope": "individual generator/detector call only; batch evaluation is not timed per dataset",
                    "peak_memory_scope": "not measured"})

    def save(self):
        self.manifest["progress_counts"] = {
            "generated_datasets": len(self.manifest["generated_datasets"]),
            "detected_datasets": len(self.manifest["detected_datasets"]),
            "evaluated_datasets": sum(r["evaluation"]["status"] == "complete" for r in self.manifest["dataset_records"].values())}
        save_run_manifest(self.run, self.manifest)

    def seal_outputs(self):
        observed = run_file_inventory(self.run)
        changed = [name for name, info in self.sealed.items() if observed.get(name) != info]
        if changed:
            self.manifest["integrity"]["output_changes"] = {
                name: {"expected": self.sealed[name], "actual": observed.get(name)} for name in changed}
            raise ValueError("previously sealed run outputs changed: " + ", ".join(changed))
        self.sealed = observed
        self.manifest["files"] = observed

    @contextmanager
    def stage(self, name):
        self.phase = name
        self.manifest.update(current_stage=name, current_dataset=None)
        record = self.manifest["stages"][name]
        record.update(status="running", started_at=datetime.now(timezone.utc).isoformat())
        if name == "evaluation":
            for dataset in self.manifest["dataset_records"].values():
                dataset[name].update(status="running", wall_seconds=None, scope="shared batch; per-dataset duration not measured")
        self.save()
        started = perf_counter()
        try:
            yield
            self.seal_outputs()
        except BaseException as exc:
            record.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
            if name != "configuration":
                for dataset in self.manifest["dataset_records"].values():
                    if dataset[name]["status"] == "running":
                        dataset[name]["status"] = "failed"
            raise
        else:
            record["status"] = "complete"
            if name == "evaluation":
                for dataset in self.manifest["dataset_records"].values():
                    dataset[name]["status"] = "complete"
            if name == "generation":
                self.manifest["completed_stages"].extend(["generation", "truth"])
            elif name != "configuration":
                self.manifest["completed_stages"].append(name)
            self.manifest["current_dataset"] = None
        finally:
            record.update(wall_seconds=perf_counter() - started, finished_at=datetime.now(timezone.utc).isoformat())
        self.save()

    @contextmanager
    def dataset(self, stage, dataset_id):
        self.manifest["current_dataset"] = dataset_id
        record = self.manifest["dataset_records"][dataset_id][stage]
        record.update(status="running", started_at=datetime.now(timezone.utc).isoformat())
        self.save()
        started = perf_counter()
        try:
            yield record
        except BaseException as exc:
            record.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
            raise
        else:
            record["status"] = "complete"
        finally:
            record.update(wall_seconds=perf_counter() - started, finished_at=datetime.now(timezone.utc).isoformat())
        self.save()

    def complete(self):
        self.phase = "verification"
        self.manifest["current_stage"] = self.phase
        self.save()
        started = perf_counter()
        expected_source = self.manifest["source"]["files"]
        actual_source = source_snapshot()[2]
        if actual_source != expected_source:
            self.manifest["integrity"].update(source_unchanged=False, source_changes={
                name: {"expected": expected_source.get(name), "actual": actual_source.get(name)}
                for name in sorted(set(expected_source) | set(actual_source))
                if expected_source.get(name) != actual_source.get(name)})
            raise ValueError("installed source changed during the benchmark run")
        self.seal_outputs()
        self.manifest["integrity"] = {"status": "verified", "output_files": len(self.sealed), "source_unchanged": True}
        self.manifest["timing"].update(verification_wall_seconds=perf_counter() - started,
                                      run_wall_seconds=perf_counter() - self.started)
        self.manifest.update(status="complete", current_stage=None, current_dataset=None,
                             finished_at=datetime.now(timezone.utc).isoformat())
        self.phase = "manifest_publication"
        self.save()

    def fail(self, exc):
        self.manifest.update(status="failed", current_stage=self.manifest.get("current_stage") or self.phase,
                             error={"type": type(exc).__name__, "message": str(exc)},
                             finished_at=datetime.now(timezone.utc).isoformat())
        self.manifest["timing"].update(run_wall_seconds=perf_counter() - self.started,
            run_scope="from recorder initialization to failure capture; excludes failed-manifest publication")
        stage = self.manifest["stages"].get(self.manifest["current_stage"])
        if stage and stage["status"] == "running":
            stage.update(status="failed", finished_at=datetime.now(timezone.utc).isoformat())
        for dataset in self.manifest["dataset_records"].values():
            record = dataset.get(self.manifest["current_stage"])
            if isinstance(record, dict) and record["status"] == "running":
                record.update(status="failed", error=self.manifest["error"])
        try:
            observed = run_file_inventory(self.run)
            changed = [name for name, info in self.sealed.items() if observed.get(name) != info]
            self.manifest["files"] = observed
            self.manifest["integrity"].update(status="partial", changed_sealed_outputs=changed,
                output_changes={name: {"expected": self.sealed[name], "actual": observed.get(name)} for name in changed})
        except Exception as inventory_error:
            self.manifest["integrity"].update(status="unavailable", error=str(inventory_error))
        try:
            self.save()
        except Exception as publication_error:
            # Preserve the original stage exception and the last durable manifest.
            try:
                (self.run / "failure.json").write_bytes(_json_bytes({**self.manifest,
                    "manifest_publication_error": str(publication_error)}))
            except OSError:
                pass
