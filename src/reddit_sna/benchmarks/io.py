"""Strict CSV adapters for synthetic node lists and non-overlapping memberships.

Callers supply the observed months, expected users and reference explicitly.
Truth should be checked against all active users; detector memberships against
the expected graph endpoints. Empty observed months are allowed explicitly.
Writers validate before opening a new file and never overwrite existing files.
"""

from collections.abc import Iterable, Mapping
import csv
from pathlib import Path

from reddit_sna.contracts import Membership, next_month

NODE_COLUMNS = ("month", "user_id")
MEMBERSHIP_COLUMNS = ("reference_id", "month", "community_id", "user_id")


def _checked_users(month: str, user_ids: Iterable[str]) -> tuple[str, ...]:
    next_month(month)
    if isinstance(user_ids, (str, bytes)):
        raise ValueError("users must be an iterable of identifiers, not one string")
    try:
        users = tuple(user_ids)
    except TypeError as exc:
        raise ValueError("users must be an iterable of identifiers") from exc
    if any(not isinstance(uid, str) or not uid.strip() for uid in users):
        raise ValueError("user identifiers must be nonempty strings")
    if len(set(users)) != len(users):
        raise ValueError("duplicate user in node list")
    return tuple(sorted(users))


def _read_rows(path: Path, columns: tuple[str, ...]) -> list[list[str]]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            if next(reader, None) != list(columns):
                raise ValueError("CSV header does not match the expected schema")
            rows = list(reader)
    except csv.Error as exc:
        raise ValueError("malformed CSV") from exc
    if any(len(row) != len(columns) for row in rows):
        raise ValueError("CSV row width does not match the expected schema")
    return rows


def _write_rows(path: Path, columns: tuple[str, ...], rows: Iterable[tuple]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def write_nodes(path: Path, month: str, user_ids: Iterable[str]) -> None:
    """Write one observed month's users in canonical order to a new CSV.

    An empty list writes a header-only observed month. The parent directory
    must already exist; this function does not choose or create a run folder.
    """
    users = _checked_users(month, user_ids)
    _write_rows(path, NODE_COLUMNS, ((month, uid) for uid in users))


def read_nodes(path: Path, *, expected_month: str) -> tuple[str, ...]:
    """Read one observed month's complete node list, including isolates."""
    next_month(expected_month)
    rows = _read_rows(path, NODE_COLUMNS)
    if any(month != expected_month for month, _ in rows):
        raise ValueError("node month does not match the expected month")
    return _checked_users(expected_month, (uid for _, uid in rows))


def validate_memberships(
    memberships: Iterable[Membership],
    *,
    expected_reference: str,
    expected_users_by_month: Mapping[str, Iterable[str]],
) -> tuple[Membership, ...]:
    """Require exactly one membership per expected user in one reference.

    Declared months must be consecutive, with at least one observed month.
    Empty months must be included explicitly with an empty user iterable.
    Return records sorted by month, community and user without changing IDs.
    """
    if not isinstance(expected_reference, str) or not expected_reference.strip():
        raise ValueError("expected reference must be a nonempty string")
    if not isinstance(expected_users_by_month, Mapping) or not expected_users_by_month:
        raise ValueError("at least one observed month and its users must be declared")
    expected = {
        month: set(_checked_users(month, users))
        for month, users in expected_users_by_month.items()
    }
    months = sorted(expected)
    if any(next_month(a) != b for a, b in zip(months, months[1:])):
        raise ValueError("declared membership months must be consecutive")

    rows = tuple(memberships)
    seen = {month: set() for month in months}
    for row in rows:
        if not isinstance(row, Membership):
            raise ValueError("memberships must contain Membership records")
        if row.reference_id != expected_reference:
            raise ValueError("membership reference does not match the expected reference")
        if row.month not in expected:
            raise ValueError("membership month is outside the declared months")
        if row.user_id in seen[row.month]:
            raise ValueError("duplicate membership for a user in one month")
        if row.user_id not in expected[row.month]:
            raise ValueError("membership contains an unexpected user")
        seen[row.month].add(row.user_id)
    if any(seen[month] != users for month, users in expected.items()):
        raise ValueError("memberships are missing expected users")
    return tuple(sorted(rows, key=lambda row: (row.month, row.community_id, row.user_id)))


def write_memberships(
    path: Path,
    memberships: Iterable[Membership],
    *,
    expected_reference: str,
    expected_users_by_month: Mapping[str, Iterable[str]],
) -> None:
    """Validate and write canonical memberships to a new UTF-8 CSV."""
    rows = validate_memberships(
        memberships,
        expected_reference=expected_reference,
        expected_users_by_month=expected_users_by_month,
    )
    _write_rows(
        path,
        MEMBERSHIP_COLUMNS,
        ((row.reference_id, row.month, row.community_id, row.user_id) for row in rows),
    )


def read_memberships(
    path: Path,
    *,
    expected_reference: str,
    expected_users_by_month: Mapping[str, Iterable[str]],
) -> tuple[Membership, ...]:
    """Read and validate a complete membership table against caller expectations."""
    rows = (Membership(*fields) for fields in _read_rows(path, MEMBERSHIP_COLUMNS))
    return validate_memberships(
        rows,
        expected_reference=expected_reference,
        expected_users_by_month=expected_users_by_month,
    )
