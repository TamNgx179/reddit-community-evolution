"""Content-addressed snapshot cohorts with explicit graph semantics."""

import csv
import hashlib
import json
import math
from pathlib import Path

from reddit_sna.contracts import next_month
from reddit_sna.data.archive import digest_file

GRAPH_PROTOCOL = "reply-r-v2"
LEGACY_GRAPH_PROTOCOL = "legacy-reply-r-v1"
EDGE_COLUMNS = ["month", "source_user_id", "target_user_id", "weight"]


def snapshot_inventory(directory: Path, *, protocol=GRAPH_PROTOCOL, expected_months=None) -> dict:
    """Validate every R row and bind a cohort to its files and semantic version.

    A cohort reference is shared across months. Individual month digests are
    separate: adding a month changes cohort identity, not the past partition.
    """
    if not isinstance(protocol, str) or not protocol.strip():
        raise ValueError("graph protocol must be a nonempty version")
    months = sorted(p.name for p in directory.iterdir() if p.is_dir())
    if not months:
        raise ValueError("snapshot cohort must contain at least one month")
    for month in months:
        next_month(month)
    if any(next_month(a) != b for a, b in zip(months, months[1:])):
        raise ValueError("snapshot months must be consecutive")
    if expected_months is not None and list(expected_months) != months:
        raise ValueError("snapshot metadata months do not match month directories")
    inventory = []
    for month in months:
        source = directory / month
        seen = set()
        with (source / "R.csv").open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != EDGE_COLUMNS:
                raise ValueError("R CSV schema does not match the edge contract")
            for row in reader:
                u, v = row["source_user_id"], row["target_user_id"]
                try:
                    weight = float(row["weight"])
                except (ValueError, TypeError):
                    raise ValueError("invalid R weight") from None
                pair = tuple(sorted((u, v))) if u and v else None
                if row["month"] != month:
                    raise ValueError("edge month does not match snapshot directory")
                if (not u or not v or not u.strip() or not v.strip() or u == v or pair in seen
                        or not math.isfinite(weight) or weight <= 0):
                    raise ValueError("R must have unique non-self edges with finite positive weights")
                seen.add(pair)
        hashes = {name: digest_file(source / name)
                  for name in ("R.csv", "directed_R.csv", "users.csv") if (source / name).is_file()}
        digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
        inventory.append({"month": month, "graph_sha256": digest, "files": hashes})
    fingerprint = hashlib.sha256(json.dumps(
        {"protocol": protocol, "months": inventory}, sort_keys=True).encode()).hexdigest()
    return {"graph_protocol": protocol, "graph_reference": f"{protocol}:{fingerprint}",
            "snapshot_cohort_sha256": fingerprint, "month_graphs": inventory,
            "actual_months": months, "start_month": months[0],
            "end_month_exclusive": next_month(months[-1])}
