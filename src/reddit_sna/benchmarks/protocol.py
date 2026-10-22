"""Bind the existing graph recipe to scoring policies and a read-only run plan."""

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import MappingProxyType

from reddit_sna.benchmarks.config import (
    _invalid_constant, _table, _unique_object, dataset_schedule, validate_benchmark_config,
)
from reddit_sna.config import ConfigError
from reddit_sna.evaluation.detection import AMI_POLICY, SUMMARY_POLICY

PROTOCOL_ID = "week1-detection-evaluation-v1"
SPLIT_POLICY = MappingProxyType({
    "generator_seed_sets": "disjoint",
    "dataset_identity": "split,scenario,difficulty,generator_seed",
    "detector_seed_role": "repeat_within_dataset",
    "canonical_selection": "first_configured_seed_not_selected_by_score",
    "evaluation_access": "after_development_and_freeze",
})


@dataclass(frozen=True)
class BenchmarkProtocol:
    protocol: dict
    benchmark: dict
    protocol_path: Path
    benchmark_path: Path
    protocol_sha256: str
    benchmark_sha256: str


def _json_file(path):
    try:
        content = path.read_bytes()
        data = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=_invalid_constant)
    except (OSError, ValueError) as exc:
        raise ConfigError(f"cannot load benchmark protocol input {path}: {exc}") from exc
    return content, data


def _exact(actual, expected, label):
    # JSON comparison also distinguishes bool/int and int/float policy fields.
    if json.dumps(actual, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
        raise ConfigError(f"{label} differs from the supported protocol")


def load_benchmark_protocol(path: Path) -> BenchmarkProtocol:
    """Validate recipe bytes, runtime policies and planned units without running them.

    The returned dictionaries are caller-owned snapshots, not a freeze record.
    Existing schema-1 graph recipes remain unchanged and independently readable.
    The sibling protocol file adds policy binding without changing archived inputs.
    """
    path = path.resolve()
    content, protocol = _json_file(path)
    _table(protocol, {"schema_version", "protocol_id", "benchmark", "ami_policy",
                      "summary_policy", "split_policy", "expected_counts"}, "benchmark protocol")
    supported = {1: PROTOCOL_ID, 2: "midterm-detection-evaluation-v2"}
    if (type(protocol["schema_version"]) is not int
            or supported.get(protocol["schema_version"]) != protocol["protocol_id"]):
        raise ConfigError("unsupported benchmark protocol schema or ID")
    recipe = protocol["benchmark"]
    _table(recipe, {"file", "sha256"}, "protocol benchmark binding")
    name, expected_hash = recipe["file"], recipe["sha256"]
    if (not isinstance(name, str) or not name or name in (".", "..")
            or "/" in name or "\\" in name or ":" in name or Path(name).is_absolute() or Path(name).name != name):
        raise ConfigError("benchmark file must be a sibling filename")
    if (not isinstance(expected_hash, str) or len(expected_hash) != 64
            or any(char not in "0123456789abcdef" for char in expected_hash)):
        raise ConfigError("benchmark binding requires a lowercase SHA-256")
    benchmark_path = (path.parent / name).resolve()
    if benchmark_path.parent != path.parent:
        raise ConfigError("benchmark file must remain in the protocol directory")
    benchmark_bytes, benchmark = _json_file(benchmark_path)
    actual_hash = sha256(benchmark_bytes).hexdigest()
    if actual_hash != expected_hash:
        raise ConfigError("benchmark SHA-256 differs from protocol binding")
    validate_benchmark_config(benchmark)
    if protocol["schema_version"] != benchmark["schema_version"]:
        raise ConfigError("benchmark/protocol schema versions must match")
    if benchmark["detector"] != {"gamma": 1.0, "seeds": [0, 1, 2], "canonical_seed": 0}:
        raise ConfigError("week-one detector schedule differs from the supported protocol")
    _exact(protocol["ami_policy"], dict(AMI_POLICY), "AMI policy")
    _exact(protocol["summary_policy"], dict(SUMMARY_POLICY), "summary policy")
    _exact(protocol["split_policy"], dict(SPLIT_POLICY), "split policy")
    planned = {}
    all_ids = set()
    for split in ("development", "evaluation"):
        schedule = dataset_schedule(benchmark, split)
        ids = {item["dataset_id"] for item in schedule}
        if len(ids) != len(schedule) or not all_ids.isdisjoint(ids):
            raise ConfigError("split dataset identities must be unique and disjoint")
        all_ids.update(ids)
        snapshots = len(schedule) * len(benchmark["months"])
        planned[split] = {"datasets": len(schedule), "snapshots": snapshots,
                          "snapshot_detector_runs": snapshots * len(benchmark["detector"]["seeds"])}
    planned["total"] = {key: sum(planned[split][key] for split in ("development", "evaluation"))
                        for key in ("datasets", "snapshots", "snapshot_detector_runs")}
    _exact(protocol["expected_counts"], planned, "expected counts")
    return BenchmarkProtocol(protocol, benchmark, path, benchmark_path, sha256(content).hexdigest(), actual_hash)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol", type=Path)
    args = parser.parse_args(argv)
    try:
        plan = load_benchmark_protocol(args.protocol)
    except (OSError, ValueError) as exc:
        print(f"benchmark protocol invalid: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"scope": "benchmark-plan-only", "status": "planned", "protocol_id": PROTOCOL_ID,
                      "protocol_sha256": plan.protocol_sha256, "benchmark_sha256": plan.benchmark_sha256,
                      "planned_counts": plan.protocol["expected_counts"], "evaluation_executed": False,
                      "freeze_record_created": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
