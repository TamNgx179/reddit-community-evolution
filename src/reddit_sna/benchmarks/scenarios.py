"""Planted memberships and transitions for the stable and grow scenarios.

Truth comes from the scenario design, independently of graph edges, detectors,
trackers and overlap thresholds. CSV export is handled separately.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from reddit_sna.contracts import Event, Membership, SampleKey, TrackingLink, next_month


@dataclass(frozen=True)
class TruthEvent:
    """One planted label for a source community and its observed next month.

    The disk fields are reference_id, source_month, source_community_id,
    target_month and event. The first three are held in source.
    """

    source: SampleKey
    target_month: str
    event: Event

    def __post_init__(self) -> None:
        if not isinstance(self.source, SampleKey):
            raise ValueError("event source must be a SampleKey")
        if self.target_month != next_month(self.source.feature_month):
            raise ValueError("event target_month must follow the source month")
        if not isinstance(self.event, Event):
            raise ValueError("event must be an Event")


@dataclass(frozen=True)
class PlantedTransitions:
    """Events and source-to-target links, ordered by source then target key."""

    events: tuple[TruthEvent, ...]
    links: tuple[TrackingLink, ...]


def _scenario_months(
    scenario: str, reference_id: str, start_month: str,
) -> tuple[str, str]:
    if scenario not in ("stable", "grow"):
        raise ValueError("scenario must be 'stable' or 'grow'")
    source = SampleKey(reference_id, start_month, "A")
    return source.feature_month, next_month(source.feature_month)


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
    start_month, target_month = _scenario_months(scenario, reference_id, start_month)
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


def build_transitions(
    scenario: str,
    reference_id: str,
    *,
    start_month: str = "2020-01",
    observed_months: Iterable[str] | None = None,
) -> PlantedTransitions:
    """Return the planned events and links for an observed scenario transition.

    Both fixture months are observed by default. An explicit observation list
    must be a nonempty, duplicate-free subset of those two months. Observing
    only one month yields no events or links, including no dissolve label.

    A -> C has the scenario's stable/grow label and K -> K is always stable.
    These declarations do not inspect memberships or run a tracking algorithm.
    The final month has no observed successor and never becomes a source.
    """
    source_month, target_month = _scenario_months(scenario, reference_id, start_month)
    fixture_months = {source_month, target_month}
    if observed_months is None:
        observed = fixture_months
    else:
        if isinstance(observed_months, (str, bytes)):
            raise ValueError("observed months must be an iterable, not one string")
        try:
            months = tuple(observed_months)
        except TypeError as exc:
            raise ValueError("observed months must be an iterable") from exc
        if not months:
            raise ValueError("at least one observed month must be declared")
        for month in months:
            next_month(month)
        if len(set(months)) != len(months):
            raise ValueError("duplicate observed month")
        observed = set(months)
        if not observed <= fixture_months:
            raise ValueError("observed month is outside the two-month scenario")

    if observed != fixture_months:
        return PlantedTransitions(events=(), links=())

    planned = (("A", "C", Event(scenario)), ("K", "K", Event.STABLE))
    events, links = [], []
    for source_id, target_id, event in planned:
        source = SampleKey(reference_id, source_month, source_id)
        target = SampleKey(reference_id, target_month, target_id)
        events.append(TruthEvent(source, target_month, event))
        links.append(TrackingLink(source, target))
    return PlantedTransitions(events=tuple(events), links=tuple(links))
