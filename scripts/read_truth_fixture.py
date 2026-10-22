"""Read and verify one stable/grow fixture using only Python's standard library.

Usage: python -I scripts/read_truth_fixture.py <dataset-directory>
This script does not import reddit_sna, notebooks, graph libraries or trackers.
"""

import argparse
from collections import defaultdict
import csv
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import sys


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _read_csv(path, columns):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        _require(next(reader, None) == columns, f"wrong CSV header: {path.name}")
        rows = list(reader)
    _require(all(len(row) == len(columns) and all(value.strip() for value in row) for row in rows),
             f"invalid CSV row: {path.name}")
    return [dict(zip(columns, row)) for row in rows]


def read_fixture(directory: Path) -> dict:
    """Check metadata, hashes, coverage and the planted stable/grow semantics."""
    root = directory.resolve()
    meta = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    _require(type(meta["schema_version"]) is int and meta["schema_version"] == 1, "unsupported schema")
    _require(meta["artifact_type"] == "synthetic-truth-fixture" and meta["status"] == "complete",
             "fixture metadata is not complete")
    scenario = meta["scenario"]
    _require(scenario in ("stable", "grow"), "unsupported scenario")
    months = meta["observed_months"]
    _require(isinstance(months, list) and len(months) == 2, "expected two observed months")
    for month in months:
        _require(isinstance(month, str) and len(month) == 7, "invalid month")
        date.fromisoformat(month + "-01")
    first = date.fromisoformat(months[0] + "-01")
    following = date(first.year + (first.month == 12), first.month % 12 + 1, 1).strftime("%Y-%m")
    _require(months[1] == following, "observed months must be consecutive")
    reference = meta["truth_reference"]
    _require(isinstance(reference, str) and reference.strip(), "invalid truth reference")
    generator = meta["generator"]
    _require(generator["version"] == 1 and type(generator["seed"]) is int
             and 0 <= generator["seed"] < 2**32 and generator["seed_used_for_truth"] is False,
             "invalid generator version/seed provenance")
    config = generator["config"]
    _require(config == {"scenario": scenario, "start_month": months[0], "source_size": 12,
                        "target_size": 12 if scenario == "stable" else 18, "background_size": 12},
             "generator config does not match the fixture")
    _require(meta["environment"]["python_version"] and meta["environment"]["package_version"],
             "missing environment versions")

    expected_files = {f"snapshots/{month}/nodes.csv" for month in months}
    expected_files.update(("truth/membership.csv", "truth/events.csv", "truth/links.csv"))
    _require(set(meta["files"]) == expected_files, "metadata file inventory differs from schema")
    for name, info in meta["files"].items():
        path = (root / name).resolve()
        _require(path.is_relative_to(root), "file path escapes dataset")
        _require(sha256(path.read_bytes()).hexdigest() == info["sha256"], f"SHA-256 mismatch: {name}")

    nodes = {}
    for month in months:
        rows = _read_csv(root / f"snapshots/{month}/nodes.csv", ["month", "user_id"])
        _require(all(row["month"] == month for row in rows), "node month mismatch")
        nodes[month] = {row["user_id"] for row in rows}
        _require(len(nodes[month]) == len(rows), "duplicate node")
    memberships = _read_csv(root / "truth/membership.csv",
                            ["reference_id", "month", "community_id", "user_id"])
    seen = set()
    groups = defaultdict(lambda: defaultdict(set))
    for row in memberships:
        _require(row["reference_id"] == reference and row["month"] in months, "membership scope mismatch")
        key = row["month"], row["user_id"]
        _require(key not in seen, "duplicate membership")
        seen.add(key)
        groups[row["month"]][row["community_id"]].add(row["user_id"])
    for month in months:
        _require({uid for observed, uid in seen if observed == month} == nodes[month], "node coverage mismatch")
    source, target = groups[months[0]], groups[months[1]]
    _require(set(source) == {"A", "K"} and set(target) == {"C", "K"}, "unexpected planted communities")
    _require(len(source["A"]) == len(source["K"]) == 12, "incorrect source sizes")
    _require(source["K"] == target["K"] and source["A"].isdisjoint(source["K"])
             and target["C"].isdisjoint(target["K"]), "background membership mismatch")
    if scenario == "stable":
        _require(source["A"] == target["C"], "stable members changed")
    else:
        _require(source["A"] < target["C"] and len(target["C"]) == 18, "grow must retain 12 and add 6")

    event_columns = ["reference_id", "source_month", "source_community_id", "target_month", "event"]
    link_columns = ["reference_id", "source_month", "source_community_id", "target_month", "target_community_id"]
    events = _read_csv(root / "truth/events.csv", event_columns)
    links = _read_csv(root / "truth/links.csv", link_columns)
    event_rows = [tuple(row[column] for column in event_columns) for row in events]
    link_rows = [tuple(row[column] for column in link_columns) for row in links]
    _require(len(events) == 2 and set(event_rows) == {
        (reference, months[0], "A", months[1], scenario),
        (reference, months[0], "K", months[1], "stable"),
    }, "events differ from planted truth")
    _require(len(links) == 2 and set(link_rows) == {
        (reference, months[0], "A", months[1], "C"),
        (reference, months[0], "K", months[1], "K"),
    }, "links differ from planted truth")
    counts = {"nodes_by_month": {month: len(nodes[month]) for month in months},
              "memberships": len(memberships), "events": len(events), "links": len(links)}
    _require(meta["counts"] == counts, "metadata counts mismatch")
    return {"dataset_id": meta["dataset_id"], "truth_reference": reference, "verified": True,
            "counts": counts, "communities": {month: {key: len(users) for key, users in groups[month].items()}
                                               for month in months}, "events": events, "links": links}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_directory", type=Path)
    args = parser.parse_args()
    try:
        result = read_fixture(args.dataset_directory)
    except (OSError, ValueError, KeyError, TypeError, OverflowError, csv.Error) as exc:
        print(f"fixture verification failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
