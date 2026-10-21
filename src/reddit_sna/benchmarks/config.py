"""Read-only, strict JSON configuration and dataset planning for week-one benchmarks."""

import argparse
import json
import math
from pathlib import Path
import sys

from reddit_sna.benchmarks.dynamic import RNG_PROTOCOL, SAMPLER_VERSION
from reddit_sna.benchmarks.scenarios import SCENARIOS
from reddit_sna.config import ConfigError
from reddit_sna.contracts import next_month

GRAPH_PROTOCOL = "synthetic-planted-undirected-v1"
ORDERING = {
    "months": "ascending", "nodes": "user_id_lexicographic",
    "edges": "source_target_lexicographic", "undirected_endpoints": "source_lt_target",
}


def _table(value, keys, name):
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be an object")
    unknown, missing = value.keys() - keys, keys - value.keys()
    if unknown or missing:
        raise ConfigError(f"{name}: unknown keys={sorted(unknown)}, missing keys={sorted(missing)}")


def _seeds(value, name):
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{name} must be a nonempty seed list")
    if any(type(seed) is not int or not 0 <= seed < 2**32 for seed in value):
        raise ConfigError(f"{name} seeds must be integers in [0, 2**32)")
    if len(value) != len(set(value)):
        raise ConfigError(f"{name} has duplicate seeds")


def validate_benchmark_config(config: dict) -> dict:
    """Reject unsupported fields, invalid parameters and overlapping split seeds.

    Return the input object without coercion or mutation. This schema supports
    the original schema-1 easy protocol and a separately versioned schema-2
    harder regime. It does not run or freeze any evaluation.
    """
    _table(config, {"schema_version", "protocol", "months", "scenarios", "difficulty",
                    "generator", "detector", "ordering"}, "benchmark")
    if type(config["schema_version"]) is not int or config["schema_version"] not in (1, 2):
        raise ConfigError("benchmark schema_version must be 1 or 2")
    expected_difficulty = "easy" if config["schema_version"] == 1 else "harder"
    if config["protocol"] != GRAPH_PROTOCOL or config["difficulty"] != expected_difficulty:
        raise ConfigError("unsupported benchmark protocol or difficulty")
    months = config["months"]
    if not isinstance(months, list) or len(months) != 2:
        raise ConfigError("months must contain exactly two observed months")
    for month in months:
        next_month(month)
    if next_month(months[0]) != months[1]:
        raise ConfigError("months must be consecutive and ascending")
    if config["scenarios"] != list(SCENARIOS):
        raise ConfigError("scenarios must contain the six supported cases in protocol order")
    generator = config["generator"]
    _table(generator, {"sampler_version", "rng_protocol", "p_in", "p_out", "weight", "seeds"}, "generator")
    if type(generator["sampler_version"]) is not int or generator["sampler_version"] != SAMPLER_VERSION:
        raise ConfigError("unsupported sampler_version")
    if generator["rng_protocol"] != RNG_PROTOCOL:
        raise ConfigError("unsupported rng_protocol")
    for name in ("p_in", "p_out"):
        value = generator[name]
        if type(value) not in (int, float) or not 0 <= value <= 1:
            raise ConfigError(f"{name} must be a finite number in [0, 1]")
    if config["schema_version"] == 2 and (generator["p_in"], generator["p_out"]) != (.25, .10):
        raise ConfigError("harder schema-2 regime fixes p_in=.25 and p_out=.10")
    if type(generator["weight"]) not in (int, float) or generator["weight"] != 1:
        raise ConfigError("this sampler supports only weight 1.0")
    _table(generator["seeds"], {"development", "evaluation"}, "generator.seeds")
    for split, seeds in generator["seeds"].items():
        _seeds(seeds, split)
    if set(generator["seeds"]["development"]) & set(generator["seeds"]["evaluation"]):
        raise ConfigError("development and evaluation generator seeds must not overlap")
    detector = config["detector"]
    _table(detector, {"gamma", "seeds", "canonical_seed"}, "detector")
    _seeds(detector["seeds"], "detector")
    if type(detector["canonical_seed"]) is not int or detector["canonical_seed"] != detector["seeds"][0]:
        raise ConfigError("canonical_seed must be the first detector seed")
    gamma = detector["gamma"]
    try:
        valid_gamma = type(gamma) in (int, float) and gamma > 0 and math.isfinite(gamma)
    except OverflowError:
        valid_gamma = False
    if not valid_gamma:
        raise ConfigError("gamma must be finite and positive")
    _table(config["ordering"], set(ORDERING), "ordering")
    if config["ordering"] != ORDERING:
        raise ConfigError("unsupported ordering policy")
    return config


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ConfigError(f"nonstandard JSON number: {value}")


def load_benchmark_config(path: Path) -> dict:
    """Read UTF-8 JSON, validate without writing, and preserve configured order."""
    try:
        with path.open(encoding="utf-8") as handle:
            config = json.load(handle, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    except (OSError, ValueError) as exc:
        raise ConfigError(f"cannot load benchmark config {path}: {exc}") from exc
    return validate_benchmark_config(config)


def dataset_schedule(config: dict, split: str) -> tuple[dict, ...]:
    """Plan dataset identities only; each detector seed is a repeat on a dataset."""
    validate_benchmark_config(config)
    if split not in ("development", "evaluation"):
        raise ConfigError("split must be development or evaluation")
    prefix = "dev" if split == "development" else "eval"
    return tuple(
        {"dataset_id": f"{prefix}-{scenario}-{config['difficulty']}-g{seed}",
         "split": split, "scenario": scenario, "difficulty": config["difficulty"], "generator_seed": seed}
        for scenario in config["scenarios"] for seed in config["generator"]["seeds"][split]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args(argv)
    try:
        config = load_benchmark_config(args.config)
        counts = {split: len(dataset_schedule(config, split)) for split in ("development", "evaluation")}
    except ValueError as exc:
        print(f"benchmark config invalid: {exc}", file=sys.stderr)
        return 2
    snapshots = sum(counts.values()) * len(config["months"])
    print(json.dumps({"scope": "benchmark-config", "status": "valid", "planned_datasets": counts,
                      "planned_snapshots": snapshots,
                      "planned_snapshot_detector_runs": snapshots * len(config["detector"]["seeds"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
