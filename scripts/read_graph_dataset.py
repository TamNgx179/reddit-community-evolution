"""Verify one six-event graph/truth dataset using only Python's standard library.

Usage: python -I scripts/read_graph_dataset.py <dataset-directory>
Checks file hashes, graph constraints and independently declared planted truth.
Does not regenerate edges or import reddit_sna, graph libraries or trackers.
"""

import argparse
import csv
from datetime import date
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import sys

SCENARIOS = ("stable", "grow", "shrink", "merge", "split", "dissolve")
RNG_PROTOCOL = "python-random-sequential-months-sorted-pairs-v1"
ORDERING = {"months": "ascending", "nodes": "user_id_lexicographic",
            "edges": "source_target_lexicographic", "undirected_endpoints": "source_lt_target"}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _unique_object(pairs):
    result = {}
    for name, value in pairs:
        _require(name not in result, f"duplicate JSON key: {name}")
        result[name] = value
    return result


def _reject_constant(value):
    raise ValueError(f"nonstandard JSON number: {value}")


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
                      parse_constant=_reject_constant)


def _csv(path, columns):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        _require(next(reader, None) == columns.split(","), f"wrong CSV header: {path.name}")
        rows = list(reader)
    _require(all(len(row) == len(columns.split(",")) and all(v.strip() for v in row) for row in rows),
             f"invalid CSV row: {path.name}")
    return rows


def _populations(scenario, months):
    original = set(f"u{i:03d}" for i in range(1, 13))
    other = set(f"u{i:03d}" for i in range(13, 25))
    growing = set(f"u{i:03d}" for i in range(1, 19))
    source, target = {
        "stable": ({"A": original}, {"C": original}),
        "grow": ({"A": original}, {"C": growing}),
        "shrink": ({"A": growing}, {"C": original}),
        "merge": ({"A": original, "B": other}, {"C": original | other}),
        "split": ({"A": original | other}, {"B": original, "C": other}),
        "dissolve": ({"A": original}, {}),
    }[scenario]
    background = set(f"u{i:03d}" for i in range(101, 113))
    return {months[0]: dict(source, K=background), months[1]: dict(target, K=background)}


def read_dataset(directory: Path) -> dict:
    """Validate a graph-only package; never infer expected users from its edges."""
    root = directory.resolve()
    meta = _json(root / "metadata.json")
    _require(type(meta["schema_version"]) is int and meta["schema_version"] == 1, "unsupported schema")
    _require(meta["artifact_type"] == "synthetic-graph-truth" and meta["status"] == "complete",
             "graph/truth metadata is not complete")
    scenario, months = meta["scenario"], meta["observed_months"]
    _require(scenario in SCENARIOS, "unsupported scenario")
    _require(isinstance(months, list) and len(months) == 2, "expected two observed months")
    for month in months:
        _require(isinstance(month, str) and len(month) == 7, "invalid month")
        date.fromisoformat(month + "-01")
    first = date.fromisoformat(months[0] + "-01")
    following = date(first.year + (first.month == 12), first.month % 12 + 1, 1).strftime("%Y-%m")
    _require(months[1] == following, "observed months must be consecutive")
    expected_files = {f"snapshots/{m}/{name}.csv" for m in months for name in ("R", "nodes")}
    expected_files |= {"truth/membership.csv", "truth/events.csv", "truth/links.csv", "benchmark-config.json"}
    _require(set(meta["files"]) == expected_files, "metadata file inventory differs from schema")
    for name, info in meta["files"].items():
        path = (root / name).resolve()
        _require(path.is_relative_to(root), "file path escapes dataset")
        data = path.read_bytes()
        _require(sha256(data).hexdigest() == info["sha256"], f"SHA-256 mismatch: {name}")
        _require(b"\r" not in data and not data.startswith(b"\xef\xbb\xbf"), f"expected UTF-8/LF: {name}")
    config = _json(root / "benchmark-config.json")
    _require(type(config["schema_version"]) is int and config["schema_version"] == 1
             and config["protocol"] == "synthetic-planted-undirected-v1"
             and config["months"] == months and config["scenarios"] == list(SCENARIOS)
             and config["difficulty"] == meta["difficulty"] == "easy"
             and config["ordering"] == meta["ordering"] == ORDERING, "config protocol mismatch")
    gen, planned = meta["generator"], config["generator"]
    split, seed = meta["split"], meta["generator_seed"]
    _require(split in ("development", "evaluation"), "invalid split")
    for seeds in (planned["seeds"]["development"], planned["seeds"]["evaluation"]):
        _require(isinstance(seeds, list) and seeds and all(type(s) is int and 0 <= s < 2**32 for s in seeds)
                 and len(set(seeds)) == len(seeds), "invalid seed schedule")
    _require(not set(planned["seeds"]["development"]) & set(planned["seeds"]["evaluation"]), "split seed overlap")
    _require(type(seed) is int and seed in planned["seeds"][split] and gen["seed"] == seed,
             "generator seed/split mismatch")
    dataset_id = f"{'dev' if split == 'development' else 'eval'}-{scenario}-easy-g{seed}"
    reference = f"truth-{dataset_id}"
    _require(meta["dataset_id"] == meta["identity_scope"] == dataset_id
             and meta["truth_reference"] == reference, "dataset identity mismatch")
    _require(gen["name"] == "planted-six-events" and gen["version"] == 1
             and gen["sampler_version"] == planned["sampler_version"] == 1
             and gen["rng_protocol"] == planned["rng_protocol"] == RNG_PROTOCOL
             and gen["seed_used_for_truth"] is False, "generator protocol mismatch")
    for name in ("p_in", "p_out"):
        _require(type(planned[name]) in (int, float) and 0 <= planned[name] <= 1, "invalid probability")
    _require(planned["weight"] == 1 and gen["config"] == {
        "scenario": scenario, "months": months, "p_in": planned["p_in"], "p_out": planned["p_out"], "weight": 1.0,
    }, "generator config mismatch")
    _require(meta["graph"] == {"directed": False, "simple": True, "weight": 1.0}
             and meta["detector_references"] == {}, "expected graph-only provenance")
    _require(all(isinstance(meta["environment"][key], str) and meta["environment"][key].strip()
                 for key in ("python_version", "package_version")), "missing environment versions")

    groups = _populations(scenario, months)
    nodes = {m: sorted(set().union(*partition.values())) for m, partition in groups.items()}
    counts = {"nodes_by_month": {}, "edges_by_month": {}, "communities_by_month": {}, "isolates_by_month": {}}
    for month in months:
        _require(_csv(root / f"snapshots/{month}/nodes.csv", "month,user_id") == [[month, u] for u in nodes[month]],
                 "nodes differ from planted population")
        edges = _csv(root / f"snapshots/{month}/R.csv", "month,source_user_id,target_user_id,weight")
        pairs, endpoints = [], set()
        for m, source, target, weight in edges:
            _require(m == month and source < target and source in nodes[month] and target in nodes[month],
                     "invalid edge month/endpoints")
            value = float(weight)
            _require(isfinite(value) and value == 1.0, "invalid edge weight")
            pairs.append((source, target))
            endpoints.update((source, target))
        _require(pairs == sorted(set(pairs)), "duplicate or unsorted edges")
        counts["nodes_by_month"][month] = len(nodes[month])
        counts["edges_by_month"][month] = len(edges)
        counts["communities_by_month"][month] = len(groups[month])
        counts["isolates_by_month"][month] = len(set(nodes[month]) - endpoints)
    membership = _csv(root / "truth/membership.csv", "reference_id,month,community_id,user_id")
    expected_membership = sorted([[reference, m, group, uid] for m, partition in groups.items()
                                  for group, ids in partition.items() for uid in ids])
    _require(membership == expected_membership, "memberships differ from planted truth")
    events = _csv(root / "truth/events.csv", "reference_id,source_month,source_community_id,target_month,event")
    _require(events == [[reference, months[0], group, months[1], "stable" if group == "K" else scenario]
                        for group in sorted(groups[months[0]])], "events differ from planted truth")
    targets = {"stable": [("A", "C")], "grow": [("A", "C")], "shrink": [("A", "C")],
               "merge": [("A", "C"), ("B", "C")], "split": [("A", "B"), ("A", "C")], "dissolve": []}
    links = _csv(root / "truth/links.csv", "reference_id,source_month,source_community_id,target_month,target_community_id")
    _require(links == [[reference, months[0], a, months[1], b] for a, b in targets[scenario] + [("K", "K")]],
             "links differ from planted truth")
    counts.update(memberships=len(membership), events=len(events), links=len(links))
    _require(meta["counts"] == counts, "metadata counts mismatch")
    return {"dataset_id": dataset_id, "split": split, "scenario": scenario, "generator_seed": seed,
            "observed_months": months, "verified": True, "truth_reference": reference, "counts": counts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_directory", type=Path)
    args = parser.parse_args()
    try:
        result = read_dataset(args.dataset_directory)
    except (OSError, ValueError, KeyError, TypeError, OverflowError, IndexError, csv.Error) as exc:
        print(f"graph dataset verification failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
