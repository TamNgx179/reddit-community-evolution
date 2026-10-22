"""Previous accepted-predecessor structure and labels, never outgoing targets."""

from collections import Counter, defaultdict

LAG_FEATURES = ("lag_size", "lag_density", "lag_internal_weight", "lag_missing")
DYNAMICS_FEATURES = ("past_growth", "past_retention", "inflow_fraction", "outflow_fraction")


def predecessor_features(months, features, labels, tracking):
    """Return lagged structural means and known past events per current group.

    A link from t-1 to t is available at t. Its source event is also known at t.
    Equal predecessor votes use lexical event order; absent eligible predecessor
    labels leave persistence missing, so the caller uses training Majority.
    Multiple predecessors are averaged equally, not selected by future success.
    """
    incoming = defaultdict(set)
    for row in tracking:
        if row["target_community_id"] and float(row["match_score"]) > 0:
            incoming[(row["label_month"], row["target_community_id"])].add(
                (row["feature_month"], row["community_id"]))
    past_labels = {(r["feature_month"], r["community_id"]): r["label"]
                   for r in labels if r["eligible"] == "1"}
    output = {}
    for index, month in enumerate(months):
        previous = months[index - 1] if index else None
        for (m, cid), current in features.items():
            if m != month:
                continue
            sources = incoming.get((month, cid), set())
            if any(sm != previous or (sm, sid) not in features for sm, sid in sources):
                raise ValueError("Lag predecessor must come from the immediately previous snapshot")
            rows = [features[key] for key in sorted(sources)]
            values = {f"lag_{name}": sum(float(r[name]) for r in rows) / len(rows) if rows else 0.0
                      for name in ("size", "density", "internal_weight")}
            values["lag_missing"] = int(not rows)
            votes = Counter(past_labels[k] for k in sources if k in past_labels)
            past_event = min(votes, key=lambda x: (-votes[x], x)) if votes else ""
            output[(month, cid)] = (values, past_event)
    return output
