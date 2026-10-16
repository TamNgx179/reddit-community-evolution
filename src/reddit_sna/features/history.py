"""Past-only membership history; ambiguous lineage resets age explicitly."""

HISTORY_FEATURES = ("community_age", "history_missing", "predecessor_count",
                    "past_growth", "past_retention", "inflow_fraction", "outflow_fraction")


def history_features(current, previous=None, previous_links=None, previous_age=None):
    previous = previous or {}
    previous_links = previous_links or {}
    previous_age = previous_age or {}
    incoming = {cid: [] for cid in current}
    for sid, candidates in previous_links.items():
        for tid, _ in candidates:
            incoming[tid].append(sid)
    result = {}
    for cid, members in current.items():
        predecessors = sorted(incoming[cid])
        if not predecessors:
            result[cid] = dict(community_age=1, history_missing=1, predecessor_count=0,
                               past_growth=0.0, past_retention=0.0,
                               inflow_fraction=0.0, outflow_fraction=0.0)
            continue
        past = set().union(*(previous[sid] for sid in predecessors))
        common = len(past & members)
        unique_lineage = len(predecessors) == 1 and len(previous_links[predecessors[0]]) == 1
        age = previous_age[predecessors[0]] + 1 if unique_lineage else 1
        result[cid] = dict(community_age=age, history_missing=0, predecessor_count=len(predecessors),
                           past_growth=(len(members) - len(past)) / len(past),
                           past_retention=common / len(past),
                           inflow_fraction=(len(members) - common) / len(members),
                           outflow_fraction=(len(past) - common) / len(past))
    return result
