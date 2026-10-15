"""Diagnostics for graph/partition invariance under appended future data.

Explicit identity alignment is required. Reference IDs and cluster names may
change between cohorts; this diagnostic never authorizes joining those outputs.
It tests no features, tracker, or forecast that has not been implemented.
"""

import csv
from pathlib import Path

from reddit_sna.contracts import next_month


def _rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _months(directory, cutoff):
    months = []
    for path in directory.iterdir():
        if path.is_dir():
            next_month(path.name)
            if path.name <= cutoff:
                months.append(path.name)
    return sorted(months)


def _graph(directory, alignment):
    users = _rows(directory / "users.csv")
    ids = {row["user_id"] for row in users}
    if not ids.issubset(alignment) or len({alignment[uid] for uid in ids}) != len(ids):
        raise ValueError("causal comparison needs complete one-to-one identity alignment")
    flags = {(alignment[row["user_id"]], int(row["authored_in_month"]), int(row["has_reply_edge"])) for row in users}
    graphs = {}
    for name in ("R.csv", "directed_R.csv"):
        edges = {}
        for row in _rows(directory / name):
            u, v = alignment[row["source_user_id"]], alignment[row["target_user_id"]]
            key = (u, v) if name == "directed_R.csv" else tuple(sorted((u, v)))
            if key in edges:
                raise ValueError("duplicate edge in causal comparison")
            edges[key] = float(row["weight"])
        graphs[name] = edges
    return flags, graphs


def _partition(path, alignment, month, expected_users):
    groups = {}
    assigned = set()
    references = set()
    for row in _rows(path):
        if row["month"] != month:
            raise ValueError("membership month does not match its snapshot")
        uid = alignment[row["user_id"]]
        if uid in assigned:
            raise ValueError("duplicate membership in causal comparison")
        assigned.add(uid)
        references.add(row["reference_id"])
        groups.setdefault(row["community_id"], set()).add(uid)
    if len(references) > 1:
        raise ValueError("mixed references in membership file")
    if assigned != expected_users:
        raise ValueError("membership does not cover exactly the graph endpoints")
    return frozenset(frozenset(group) for group in groups.values())


def compare_causal_prefix(left: Path, right: Path, cutoff: str, *, left_user_map, right_user_map,
                          left_memberships: Path | None = None, right_memberships: Path | None = None,
                          seed=0) -> dict:
    """Compare aligned past data; do not open future-month graph/membership files."""
    next_month(cutoff)
    if any(len(set(m.values())) != len(m) for m in (left_user_map, right_user_map)):
        raise ValueError("causal comparison needs one-to-one identity alignment")
    if (left_memberships is None) != (right_memberships is None):
        raise ValueError("both membership sources are required for partition comparison")
    months = _months(left, cutoff)
    other = _months(right, cutoff)
    if not months or months != other:
        raise ValueError("past month coverage differs or is empty")
    results = []
    for month in months:
        a, b = _graph(left / month, left_user_map), _graph(right / month, right_user_map)
        partition_equal = None
        if left_memberships is not None:
            filename = f"membership-seed{seed}.csv"
            endpoints_a = {uid for edge in a[1]["R.csv"] for uid in edge}
            endpoints_b = {uid for edge in b[1]["R.csv"] for uid in edge}
            partition_equal = _partition(left_memberships / month / filename, left_user_map, month, endpoints_a) == _partition(
                right_memberships / month / filename, right_user_map, month, endpoints_b)
        results.append({"month": month, "graph_invariant": a == b, "partition_invariant": partition_equal})
    return {"cutoff_month": cutoff, "months": results,
            "graph_invariant": all(r["graph_invariant"] for r in results),
            "partition_invariant": all(r["partition_invariant"] for r in results) if left_memberships is not None else None,
            "alignment_policy": "caller-supplied canonical identity; cluster labels ignored; references remain distinct",
            "scope": "graph and optional partition only; no tracker/features/forecast validation"}
