"""Strict, read-only configuration loading; relative paths use the TOML folder."""

from dataclasses import dataclass
from pathlib import Path
import re
import tomllib
from typing import Any

from reddit_sna.contracts import PipelineName, SCHEMA_VERSION


class ConfigError(ValueError):
    """An invalid configuration or unsafe output destination."""


def validate_run_id(value: str) -> str:
    """Validate a portable run identifier, excluding traversal and Windows device names."""
    if not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value
    ):
        raise ConfigError("run_id must be 1-64 letters, digits, underscores or hyphens")
    reserved = {"CON", "PRN", "AUX", "NUL"}
    reserved.update(f"{prefix}{i}" for prefix in ("COM", "LPT") for i in range(1, 10))
    if value.upper() in reserved:
        raise ConfigError("run_id must not be a reserved Windows device name")
    return value


@dataclass(frozen=True)
class RunConfig:
    source: Path
    project_root: Path
    pipeline: PipelineName
    seed: int
    input_kind: str
    input_path: Path | None
    output_root: Path
    run_id: str

    @property
    def run_directory(self) -> Path:
        """Return the isolated pipeline/run destination without creating it."""
        return self.output_root / self.pipeline.value / self.run_id

    def to_dict(self) -> dict[str, Any]:
        """Serialize resolved configuration for provenance; this does not execute the pipeline."""
        return {
            "schema_version": SCHEMA_VERSION,
            "config_path": str(self.source),
            "project_root": str(self.project_root),
            "pipeline": self.pipeline.value,
            "seed": self.seed,
            "input": {
                "kind": self.input_kind,
                "path": str(self.input_path) if self.input_path else None,
            },
            "output": {
                "root": str(self.output_root),
                "run_id": self.run_id,
                "directory": str(self.run_directory),
            },
        }


def _table(raw: Any, allowed: set[str], required: set[str], name: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ConfigError(f"{name} must be a TOML table")
    unknown, missing = raw.keys() - allowed, required - raw.keys()
    if unknown or missing:
        raise ConfigError(f"{name}: unknown keys={sorted(unknown)}, missing keys={sorted(missing)}")
    return raw


def _path(value: Any, base: Path, name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} must be a nonempty path string")
    try:
        return (base / value).resolve()
    except (ValueError, OSError) as exc:
        raise ConfigError(f"invalid {name}: {exc}") from exc


def validate_destination(config: RunConfig) -> Path:
    """Validate without creating directories. Also used immediately before writes."""
    validate_run_id(config.run_id)
    root = config.output_root.resolve()
    allowed = (config.project_root / "artifacts").resolve()
    protected = [(config.project_root / "data").resolve()]
    if config.input_path is not None:
        protected.append(config.input_path.resolve())
    destination = config.run_directory.resolve()
    for path in (root, destination):
        if any(path.is_relative_to(item) or item.is_relative_to(path) for item in protected):
            raise ConfigError("output must not overlap input or data directories")
        if not path.is_relative_to(allowed):
            raise ConfigError("output must stay inside project_root/artifacts")
    if not destination.is_relative_to(root):
        raise ConfigError("run destination escapes output root")
    if any(parent.exists() and not parent.is_dir() for parent in destination.parents):
        raise ConfigError("output parent is not a directory")
    if destination.exists():
        raise ConfigError(f"run already exists: {destination}; choose a new run_id")
    return destination


def load_config(path: Path, *, run_id: str | None = None) -> RunConfig:
    """Load strict TOML, resolve paths relative to its directory and validate output boundaries."""
    source = path.resolve()
    try:
        with source.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"cannot read TOML config: {exc}") from exc
    required = {"schema_version", "pipeline", "project_root", "seed", "input", "output"}
    _table(raw, required, required, "config")
    if type(raw["schema_version"]) is not int or raw["schema_version"] != SCHEMA_VERSION:
        raise ConfigError(f"schema_version must be {SCHEMA_VERSION}")
    if type(raw["seed"]) is not int or not 0 <= raw["seed"] < 2**32:
        raise ConfigError("seed must be an integer in [0, 2**32)")
    try:
        pipeline = PipelineName(raw["pipeline"])
    except (ValueError, TypeError) as exc:
        raise ConfigError(f"unknown pipeline: {raw['pipeline']!r}") from exc
    project_root = _path(raw["project_root"], source.parent, "project_root")
    if not project_root.is_dir():
        raise ConfigError(f"project_root does not exist: {project_root}")
    input_table = _table(raw["input"], {"kind", "path"}, {"kind"}, "input")
    kind = input_table["kind"]
    expected_kind = "reddit" if pipeline == PipelineName.CORE else "synthetic"
    if kind != expected_kind:
        raise ConfigError(f"{pipeline.value} expects input.kind={expected_kind!r}")
    input_path = None
    if "path" in input_table:
        input_path = _path(input_table["path"], source.parent, "input.path")
        if not input_path.exists():
            raise ConfigError(f"input path does not exist: {input_path}")
    if kind == "reddit" and (input_path is None or not input_path.is_dir()):
        raise ConfigError("core requires input.path pointing to an existing Reddit input directory")
    output = _table(raw["output"], {"root", "run_id"}, {"root", "run_id"}, "output")
    config = RunConfig(
        source=source,
        project_root=project_root,
        pipeline=pipeline,
        seed=raw["seed"],
        input_kind=kind,
        input_path=input_path,
        output_root=_path(output["root"], source.parent, "output.root"),
        run_id=validate_run_id(run_id if run_id is not None else output["run_id"]),
    )
    validate_destination(config)
    return config
