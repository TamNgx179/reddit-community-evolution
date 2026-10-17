"""Planted user memberships for the week-one stable and grow scenarios.

Memberships are deterministic scenario inputs, independent of graph edges,
detectors and trackers. CSV adapters and transition events are separate steps.
"""

from reddit_sna.contracts import Membership, next_month


def build_memberships(
    scenario: str,
    reference_id: str,
    *,
    start_month: str = "2020-01",
) -> tuple[Membership, ...]:
    """Return a two-month planted partition scoped to the caller's reference.

    Both scenarios start with 12 users in A and 12 disjoint background users
    in K. Next month the main group is called C: stable keeps A's exact users,
    while grow retains all of them and adds six new users. K stays unchanged.

    User IDs are synthetic and local to this dataset/reference. Records are
    ordered by month, community and user; no random seed or file I/O is used.
    """
    if scenario not in ("stable", "grow"):
        raise ValueError("scenario must be 'stable' or 'grow'")

    target_month = next_month(start_month)
    source_users = tuple(f"u{i:03d}" for i in range(1, 13))
    target_size = 12 if scenario == "stable" else 18
    target_users = tuple(f"u{i:03d}" for i in range(1, target_size + 1))
    background_users = tuple(f"u{i:03d}" for i in range(101, 113))
    snapshots = (
        (start_month, (("A", source_users), ("K", background_users))),
        (target_month, (("C", target_users), ("K", background_users))),
    )
    return tuple(
        Membership(reference_id, month, community_id, user_id)
        for month, communities in snapshots
        for community_id, users in communities
        for user_id in users
    )
