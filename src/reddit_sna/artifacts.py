"""Reserve isolated run directories and record provenance for future real runs."""

from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
import platform

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
