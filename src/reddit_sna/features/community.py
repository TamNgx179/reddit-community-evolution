"""Snapshot-only community features: no future membership is accepted."""

FEATURES = ("size", "internal_edges", "internal_weight", "boundary_weight", "density")


def snapshot_features(groups, edges):
    owners = {}
    result = {}
    for cid, members in groups.items():
        if not members:
            raise ValueError("Communities must be nonempty")
        for user in members:
            if user in owners:
                raise ValueError("User assigned to multiple communities")
            owners[user] = cid
        result[cid] = dict(size=len(members), internal_edges=0,
                           internal_weight=0.0, boundary_weight=0.0, density=0.0)
    seen_edges, months = set(), set()
    for edge in edges:
        months.add(edge.month)
        pair = frozenset((edge.source_user_id, edge.target_user_id))
        if pair in seen_edges:
            raise ValueError("Duplicate undirected edge")
        seen_edges.add(pair)
        if len(months) > 1:
            raise ValueError("Features cannot mix snapshot months")
        if edge.source_user_id not in owners or edge.target_user_id not in owners:
            raise ValueError("Edge endpoint lacks membership")
        left, right = owners[edge.source_user_id], owners[edge.target_user_id]
        if left == right:
            result[left]["internal_edges"] += 1
            result[left]["internal_weight"] += edge.weight
        else:
            result[left]["boundary_weight"] += edge.weight
            result[right]["boundary_weight"] += edge.weight
    for row in result.values():
        n = row["size"]
        row["density"] = 2 * row["internal_edges"] / (n * (n - 1)) if n > 1 else 0.0
    return result
