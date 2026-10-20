"""Adapters and validation for multi-month community memberships."""

import csv
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path

from reddit_sna.benchmarks.io import validate_memberships
from reddit_sna.contracts import Membership
from reddit_sna.contracts import next_month


CommunityGroups = dict[str, frozenset[str]]
MEMBERSHIP_COLUMNS = (
    "reference_id",
    "month",
    "community_id",
    "user_id",
)


def group_memberships(
    rows: Iterable[Membership],
    *,
    month: str | None = None,
    expected_reference: str | None = None,
) -> CommunityGroups:
    """Group validated membership records by community.

    ``rows`` must represent one snapshot. Use ``groups_by_month`` for a file
    containing multiple observed months.
    """
    groups: dict[str, set[str]] = defaultdict(set)
    seen_users: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, Membership):
            raise TypeError("membership rows must be Membership instances")
        if month is not None and row.month != month:
            raise ValueError("membership row does not match the requested month")
        if expected_reference is not None and row.reference_id != expected_reference:
            raise ValueError("membership row does not match the expected reference")
        previous = seen_users.get(row.user_id)
        if previous is not None and previous != row.community_id:
            raise ValueError(f"user belongs to multiple communities: {row.user_id}")
        if previous == row.community_id:
            raise ValueError(f"duplicate membership row: {row.user_id}")
        seen_users[row.user_id] = row.community_id
        groups[row.community_id].add(row.user_id)
    return {community_id: frozenset(users) for community_id, users in groups.items()}


def groups_by_month(
    rows: Iterable[Membership],
    *,
    expected_reference: str | None = None,
) -> dict[str, CommunityGroups]:
    """Group a validated multi-month membership table by observed month."""
    grouped: dict[str, list[Membership]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, Membership):
            raise TypeError("membership rows must be Membership instances")
        grouped[row.month].append(row)
    return {
        month: group_memberships(
            month_rows,
            month=month,
            expected_reference=expected_reference,
        )
        for month, month_rows in sorted(grouped.items())
    }


def read_memberships(
    path: Path,
    *,
    expected_reference: str | None = None,
    expected_users_by_month: Mapping[str, Iterable[str]] | None = None,
) -> list[Membership]:
    """Read and validate a canonical CSV containing one or more months.

    ``expected_users_by_month`` is optional for compatibility with callers that
    only need parsing. When supplied, it independently verifies complete
    coverage, including explicitly declared empty observed months.
    """
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle, strict=True)
            if next(reader, None) != list(MEMBERSHIP_COLUMNS):
                raise ValueError("membership CSV header does not match the expected schema")
            raw_rows = list(reader)
            if any(len(row) != len(MEMBERSHIP_COLUMNS) or any(value == "" for value in row)
                   for row in raw_rows):
                raise ValueError("membership CSV contains a blank or malformed row")
            rows = [
                Membership(
                    reference_id=row[0],
                    month=row[1],
                    community_id=row[2],
                    user_id=row[3],
                )
                for row in raw_rows
            ]
    except (OSError, csv.Error, ValueError) as exc:
        raise ValueError(f"cannot read membership CSV {path}: {exc}") from exc
    if not rows:
        if expected_users_by_month is None or all(
            not tuple(users) for users in expected_users_by_month.values()
        ):
            return rows
        raise ValueError("memberships are missing expected users")
    actual_reference = rows[0].reference_id
    if any(row.reference_id != actual_reference for row in rows):
        raise ValueError("membership CSV must contain one reference")
    if expected_reference is not None and actual_reference != expected_reference:
        raise ValueError("membership reference does not match the expected reference")
    if expected_users_by_month is not None:
        rows = list(
            validate_memberships(
                rows,
                expected_reference=expected_reference or actual_reference,
                expected_users_by_month=expected_users_by_month,
            )
        )
    else:
        groups_by_month(rows, expected_reference=actual_reference)
    return rows


def groups_from_rows(
    rows: Iterable[Membership],
    *,
    month: str | None = None,
    expected_reference: str | None = None,
) -> CommunityGroups:
    """Return a validated, immutable mapping suitable for tracking."""
    rows = tuple(rows)
    if month is None:
        months = {row.month for row in rows}
        if len(months) != 1:
            raise ValueError("specify month when rows contain multiple months")
        month = next(iter(months))
    next_month(month)
    rows = tuple(row for row in rows if row.month == month)
    return group_memberships(
        rows,
        month=month,
        expected_reference=expected_reference,
    )


def validate_nodes(groups: Mapping[str, Iterable[str]], nodes: Iterable[str]) -> None:
    """Ensure membership users are unique and contained in the node set."""
    node_list = list(nodes)
    node_set = set(node_list)
    if len(node_set) != len(node_list):
        raise ValueError("nodes must be unique")
    users: set[str] = set()
    for community_id, members in groups.items():
        if not community_id:
            raise ValueError("community IDs must be nonempty")
        for user_id in members:
            if user_id in users:
                raise ValueError(f"user belongs to multiple communities: {user_id}")
            users.add(user_id)
            if user_id not in node_set:
                raise ValueError(f"membership user is not an observed node: {user_id}")