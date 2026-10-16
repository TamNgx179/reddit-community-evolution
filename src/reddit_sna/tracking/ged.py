"""GED inclusion adaptation with explicit ambiguity, not a verbatim GED clone.

Reference: Brodka et al., https://doi.org/10.1007/s13278-012-0058-8.
Importance is current-community internal weighted degree (unit fallback only for
zero-degree members). Pair inclusion combines member fraction and importance
fraction. Topology-based event reduction is a documented project adaptation.
"""

from collections import Counter
import math

from reddit_sna.contracts import Event
from reddit_sna.tracking.jaccard import validate_partitions

NUMERIC_TOLERANCE = 1e-12


def passes(value, threshold):
    """Inclusive thresholds tolerate only roundoff at the declared boundary."""
    return value >= threshold or math.isclose(value, threshold, rel_tol=NUMERIC_TOLERANCE, abs_tol=NUMERIC_TOLERANCE)


def importance(groups, edges):
    owners = {u: cid for cid, users in groups.items() for u in users}
    weights = {cid: dict.fromkeys(users, 0.0) for cid, users in groups.items()}
    for edge in edges:
        left, right = owners[edge.source_user_id], owners[edge.target_user_id]
        if left == right:
            weights[left][edge.source_user_id] += edge.weight
            weights[right][edge.target_user_id] += edge.weight
    return {cid: {u: value if value > 0 else 1.0 for u, value in values.items()}
            for cid, values in weights.items()}


def inclusion(source, target, weights):
    if not source or set(weights) != source or any(not math.isfinite(v) or v <= 0 for v in weights.values()):
        raise ValueError("Importance must cover exactly the nonempty source with finite positive weights")
    common = source & target
    return len(common) / len(source) * (sum(weights[u] for u in sorted(common)) / sum(weights[u] for u in sorted(source)))


def transitions(source, target, source_weights, target_weights, alpha=0.5, beta=0.5, dissolve=0.1):
    """Return accepted links, nullable source labels and all overlapping pairs.

    Retain pair if either directional inclusion passes its threshold. No accepted
    link is dissolve only if both inclusions to every target are below dissolve;
    otherwise unresolved. Multi-successor AND multi-predecessor topology is also
    unresolved. Keep evidence rather than silently calling these cases dissolve.
    """
    if not all(math.isfinite(v) for v in (alpha, beta, dissolve)) or not 0 < dissolve <= min(alpha, beta) <= max(alpha, beta) <= 1:
        raise ValueError("Require 0 < dissolve <= alpha,beta <= 1")
    validate_partitions(source, target)
    if set(source_weights) != set(source) or set(target_weights) != set(target):
        raise ValueError("Importance community keys mismatch")
    for groups, weights in ((source, source_weights), (target, target_weights)):
        for cid, members in groups.items():
            inclusion(members, members, weights[cid])
    links = {sid: [] for sid in sorted(source)}
    pairs = []
    target_owner = {user: tid for tid, members in target.items() for user in members}
    source_totals = {cid: sum(values[u] for u in sorted(values)) for cid, values in source_weights.items()}
    target_totals = {cid: sum(values[u] for u in sorted(values)) for cid, values in target_weights.items()}
    for sid, members in sorted(source.items()):
        overlap = {}
        for user in sorted(members):
            if user in target_owner:
                overlap.setdefault(target_owner[user], []).append(user)
        for tid, common in sorted(overlap.items()):
            others = target[tid]
            forward = len(common) / len(members) * sum(source_weights[sid][u] for u in common) / source_totals[sid]
            backward = len(common) / len(others) * sum(target_weights[tid][u] for u in common) / target_totals[tid]
            accepted = passes(forward, alpha) or passes(backward, beta)
            pairs.append(dict(source_community_id=sid, target_community_id=tid,
                              shared_members=len(common), inclusion_forward=forward,
                              inclusion_backward=backward, accepted=int(accepted)))
            if accepted:
                links[sid].append((tid, max(forward, backward)))
    incoming = Counter(tid for candidates in links.values() for tid, _ in candidates)
    labels, reasons = {}, {}
    for sid, candidates in links.items():
        if not candidates:
            weak = any(p["source_community_id"] == sid and
                       passes(max(p["inclusion_forward"], p["inclusion_backward"]), dissolve) for p in pairs)
            labels[sid] = None if weak else Event.DISSOLVE
            reasons[sid] = "weak_overlap_unresolved" if weak else "below_dissolve_threshold"
        elif len(candidates) > 1 and any(incoming[tid] > 1 for tid, _ in candidates):
            labels[sid], reasons[sid] = None, "many_to_many_unresolved"
        elif len(candidates) > 1:
            labels[sid], reasons[sid] = Event.SPLIT, "multiple_successors"
        elif incoming[candidates[0][0]] > 1:
            labels[sid], reasons[sid] = Event.MERGE, "multiple_predecessors"
        else:
            difference = len(target[candidates[0][0]]) - len(source[sid])
            labels[sid] = Event.GROW if difference > 0 else Event.SHRINK if difference < 0 else Event.STABLE
            reasons[sid] = "one_to_one_size_comparison"
    return links, labels, reasons, pairs
