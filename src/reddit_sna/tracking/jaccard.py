"""Jaccard community linking and six-event assignment."""

from math import isfinite
from typing import Iterable, Mapping

from reddit_sna.contracts import Event


def jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    """Return set Jaccard similarity; two empty sets have similarity zero."""
    left_set, right_set = set(left), set(right)
    union = left_set | right_set
    return len(left_set & right_set) / len(union) if union else 0.0


def _validate_groups(groups: Mapping[str, Iterable[str]], name: str) -> dict[str, frozenset[str]]:
    result: dict[str, frozenset[str]] = {}
    users: set[str] = set()
    for community_id, members in groups.items():
        if not isinstance(community_id, str) or not community_id:
            raise ValueError(f"{name} community IDs must be nonempty strings")
        frozen = frozenset(members)
        if any(not isinstance(user, str) or not user for user in frozen):
            raise ValueError(f"{name} user IDs must be nonempty strings")
        overlap = users & frozen
        if overlap:
            raise ValueError(f"{name} users belong to multiple communities: {sorted(overlap)}")
        users.update(frozen)
        result[community_id] = frozen
    return result


def track(
    source: Mapping[str, Iterable[str]],
    target: Mapping[str, Iterable[str]],
    *,
    tau: float = 0.30,
    size_tolerance: float = 0.10,
    target_observed: bool = True,
) -> dict[str, object]:
    """Link two partitions and assign events using the v1 policy.

    ``target_observed=False`` represents an unavailable successor and never
    produces links or dissolve labels.
    """
    if not isfinite(tau) or not 0 <= tau <= 1:
        raise ValueError("tau must be finite and in [0, 1]")
    if not isfinite(size_tolerance) or not 0 <= size_tolerance < 1:
        raise ValueError("size_tolerance must be finite and in [0, 1)")
    source_groups = _validate_groups(source, "source")
    target_groups = _validate_groups(target, "target")
    if not target_observed:
        return {
            "links": [],
            "events": [],
            "diagnostics": {
                "source_count": len(source_groups),
                "target_count": 0,
                "candidate_count": 0,
                "link_count": 0,
                "unmatched_source_count": 0,
                "extra_target_count": 0,
                "ambiguous_source_count": 0,
                "target_observed": False,
                "tau": tau,
                "size_tolerance": size_tolerance,
            },
        }

    candidates = []
    for source_id, source_members in source_groups.items():
        for target_id, target_members in target_groups.items():
            score = jaccard(source_members, target_members)
            if score >= tau:
                candidates.append(
                    {
                        "source_community_id": source_id,
                        "target_community_id": target_id,
                        "jaccard": score,
                    }
                )
    links = sorted(
        candidates,
        key=lambda row: (
            -row["jaccard"],
            row["source_community_id"],
            row["target_community_id"],
        ),
    )
    source_links: dict[str, list[dict[str, object]]] = {key: [] for key in source_groups}
    target_links: dict[str, list[dict[str, object]]] = {key: [] for key in target_groups}
    for link in links:
        source_links[link["source_community_id"]].append(link)
        target_links[link["target_community_id"]].append(link)

    events = []
    ambiguous_count = 0
    for source_id in sorted(source_groups):
        outgoing = source_links[source_id]
        if not outgoing:
            event = Event.DISSOLVE.value
        elif len(outgoing) > 1:
            event = Event.SPLIT.value
            if any(len(target_links[row["target_community_id"]]) > 1 for row in outgoing):
                ambiguous_count += 1
        elif len(target_links[outgoing[0]["target_community_id"]]) > 1:
            event = Event.MERGE.value
        else:
            source_size = len(source_groups[source_id])
            target_size = len(target_groups[outgoing[0]["target_community_id"]])
            ratio = target_size / source_size if source_size else 1.0
            if ratio > 1 + size_tolerance:
                event = Event.GROW.value
            elif ratio < 1 - size_tolerance:
                event = Event.SHRINK.value
            else:
                event = Event.STABLE.value
        events.append(
            {
                "source_community_id": source_id,
                "event": event,
                "target_community_ids": [
                    row["target_community_id"] for row in outgoing
                ],
            }
        )

    matched_targets = {row["target_community_id"] for row in links}
    diagnostics = {
        "source_count": len(source_groups),
        "target_count": len(target_groups),
        "candidate_count": len(candidates),
        "link_count": len(links),
        "unmatched_source_count": sum(not source_links[key] for key in source_groups),
        "extra_target_count": len(target_groups) - len(matched_targets),
        "ambiguous_source_count": ambiguous_count,
        "target_observed": True,
        "tau": tau,
        "size_tolerance": size_tolerance,
    }
    return {"links": links, "events": events, "diagnostics": diagnostics}
