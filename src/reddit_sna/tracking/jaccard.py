"""Explicit overlap fallback, not an implementation of GED or HeTCo."""

from collections import Counter

from reddit_sna.contracts import Event


def validate_partitions(source, target):
    """Require nonempty groups and at most one community per user per month."""
    for groups in (source, target):
        seen = set()
        for members in groups.values():
            if not members:
                raise ValueError("Communities must be nonempty")
            if seen & members:
                raise ValueError("User assigned to multiple communities")
            seen.update(members)


def transitions(source, target, threshold=0.25):
    """Label each source community; split takes precedence over merge.

    Keep every pair whose member-set Jaccard >= threshold. A source with no
    link dissolves; multiple successors split; a sole successor with multiple
    predecessors merges; remaining pairs compare exact community sizes.
    Births have no source and therefore produce no forecasting sample.
    """
    if not 0 < threshold <= 1:
        raise ValueError("Jaccard threshold must be in (0, 1]")
    validate_partitions(source, target)
    links = {}
    for sid, members in sorted(source.items()):
        if not members:
            raise ValueError("Communities must be nonempty")
        links[sid] = []
        for tid, others in sorted(target.items()):
            if not others:
                raise ValueError("Communities must be nonempty")
            score = len(members & others) / len(members | others)
            if score >= threshold:
                links[sid].append((tid, score))
    incoming = Counter(tid for pairs in links.values() for tid, _ in pairs)
    events = {}
    for sid, pairs in links.items():
        if not pairs:
            event = Event.DISSOLVE
        elif len(pairs) > 1:
            event = Event.SPLIT
        elif incoming[pairs[0][0]] > 1:
            event = Event.MERGE
        else:
            delta = len(target[pairs[0][0]]) - len(source[sid])
            event = Event.GROW if delta > 0 else Event.SHRINK if delta < 0 else Event.STABLE
        events[sid] = event
    return links, events
