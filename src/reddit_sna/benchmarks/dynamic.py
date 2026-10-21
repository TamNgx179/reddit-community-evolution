"""Seeded undirected snapshots sampled from planted, validated memberships.

Stable means stable community members, not identical edges across snapshots.
The sampler never repairs isolates or uses detector/evaluation output.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from itertools import combinations
import random

from reddit_sna.benchmarks.io import validate_memberships
from reddit_sna.contracts import Membership, SnapshotEdge

SAMPLER_VERSION = 1
RNG_PROTOCOL = "python-random-sequential-months-sorted-pairs-v1"


@dataclass(frozen=True)
class SampledSnapshot:
    """One observed month's active nodes, including isolates, and sampled edges."""

    month: str
    nodes: tuple[str, ...]
    edges: tuple[SnapshotEdge, ...]


def sample_snapshots(
    memberships: Iterable[Membership],
    *,
    expected_reference: str,
    expected_users_by_month: Mapping[str, Iterable[str]],
    generator_seed: int = 11,
    p_in: float = 0.50,
    p_out: float = 0.02,
) -> tuple[SampledSnapshot, ...]:
    """Sample one Bernoulli edge per unordered user pair in each month.

    Memberships must exactly cover independently supplied active user lists.
    Months are consecutive and may be explicitly empty. Return snapshots,
    nodes and edges in canonical order without modifying the input records.

    One local random.Random stream is seeded once. Visit months in ascending
    order, then every pair of sorted user IDs; consume one draw for every pair,
    including probabilities 0 and 1. Use p_in within a planted group, otherwise
    p_out. Emitted endpoints satisfy source < target and all weights are 1.0.
    This protocol does not guarantee identical results across Python versions.
    No global random state, graph library, file output or tracking is used.
    """
    if type(generator_seed) is not int or not 0 <= generator_seed < 2**32:
        raise ValueError("generator_seed must be an integer in [0, 2**32)")
    for name, value in (("p_in", p_in), ("p_out", p_out)):
        if type(value) not in (int, float) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be a finite number in [0, 1]")
    rows = validate_memberships(
        memberships, expected_reference=expected_reference,
        expected_users_by_month=expected_users_by_month,
    )
    rng = random.Random(generator_seed)
    snapshots = []
    for month in sorted(expected_users_by_month):
        groups = {row.user_id: row.community_id for row in rows if row.month == month}
        nodes = tuple(sorted(groups))
        edges = []
        for source, target in combinations(nodes, 2):
            probability = p_in if groups[source] == groups[target] else p_out
            if rng.random() < probability:
                edges.append(SnapshotEdge(month, source, target, 1.0))
        snapshots.append(SampledSnapshot(month, nodes, tuple(edges)))
    return tuple(snapshots)
