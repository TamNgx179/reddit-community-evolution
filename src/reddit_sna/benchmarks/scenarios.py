"""Planted memberships and transitions for the six week-one event scenarios.

Truth comes from the scenario design, independently of graph edges, detectors,
trackers and overlap thresholds. CSV export is handled separately.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from reddit_sna.contracts import Event, Membership, SampleKey, TrackingLink, next_month

SCENARIOS = ("stable", "grow", "shrink", "merge", "split", "dissolve")


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
    """One event per source, with zero or more links; ordered by source/target."""

    events: tuple[TruthEvent, ...]
    links: tuple[TrackingLink, ...]


def _scenario_months(
    scenario: str, reference_id: str, start_month: str,
) -> tuple[str, str]:
    if scenario not in SCENARIOS:
        raise ValueError(f"scenario must be one of: {', '.join(SCENARIOS)}")
    source = SampleKey(reference_id, start_month, "A")
    return source.feature_month, next_month(source.feature_month)


def _scenario_definition(scenario: str):
    """Declare populations and labels together, before graph/tracker execution."""
    main24 = tuple(f"u{i:03d}" for i in range(1, 25))
    main12, main18, other12 = main24[:12], main24[:18], main24[12:]
    background = ("K", tuple(f"u{i:03d}" for i in range(101, 113)))
    definitions = {
        "stable": ((("A", main12),), (("C", main12),),
                   (("A", ("C",), Event.STABLE),)),
        "grow": ((("A", main12),), (("C", main18),),
                 (("A", ("C",), Event.GROW),)),
        "shrink": ((("A", main18),), (("C", main12),),
                   (("A", ("C",), Event.SHRINK),)),
        "merge": ((("A", main12), ("B", other12)), (("C", main24),),
                  (("A", ("C",), Event.MERGE), ("B", ("C",), Event.MERGE))),
        "split": ((("A", main24),), (("B", main12), ("C", other12)),
                  (("A", ("B", "C"), Event.SPLIT),)),
        "dissolve": ((("A", main12),), (), (("A", (), Event.DISSOLVE),)),
    }
    source, target, transitions = definitions[scenario]
    return source + (background,), target + (background,), transitions + (("K", ("K",), Event.STABLE),)


def build_memberships(
    scenario: str,
    reference_id: str,
    *,
    start_month: str = "2020-01",
) -> tuple[Membership, ...]:
    """Return a two-month planted partition scoped to the caller's reference.

    Stable/grow/shrink have A -> C with 12 -> 12, 12 -> 18 and 18 -> 12
    members. Merge combines A12 + B12 -> C24; split divides A24 -> B12 + C12.
    Dissolve removes A12 and its users from next month's active population.
    Every case has 12 disjoint background users in K, unchanged in both months.

    User IDs are synthetic and local to this dataset/reference. Records are
    ordered by month, community and user; no random seed or file I/O is used.
    """
    start_month, target_month = _scenario_months(scenario, reference_id, start_month)
    source_groups, target_groups, _ = _scenario_definition(scenario)
    snapshots = ((start_month, source_groups), (target_month, target_groups))
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

    Each observed source has one label, including both sources in a merge.
    Split has one event with two links; dissolve has an event without a link.
    K -> K is always stable. Declarations do not inspect memberships or run a tracker.
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

    _, _, planned = _scenario_definition(scenario)
    events, links = [], []
    for source_id, target_ids, event in planned:
        source = SampleKey(reference_id, source_month, source_id)
        events.append(TruthEvent(source, target_month, event))
        for target_id in target_ids:
            target = SampleKey(reference_id, target_month, target_id)
            links.append(TrackingLink(source, target))
    return PlantedTransitions(events=tuple(events), links=tuple(links))
