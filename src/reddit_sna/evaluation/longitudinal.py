"""Development-only observability diagnostics, never forecasting features.

Direct membership matches are candidates, not evidence of persistent social
identity. A complete window without a match does not establish social death.
"""

from collections import Counter, defaultdict

from reddit_sna.contracts import shift_month
from reddit_sna.tracking.ged import importance, transitions


def audit_rows(month_data, observations, labels, reference, cutoff, horizons=(1, 2, 3)):
    """Compare fixed source groups with each future partition within development.

    Missing months invalidate window coverage. Empty-record months are unknown,
    including when a graph file exists. Activity and partition observation use
    different channels and denominators. All source groups remain in the output.
    """
    if tuple(horizons) != (1, 2, 3) or not month_data or any(m >= cutoff for m in month_data):
        raise ValueError('Require development months and declared horizons 1,2,3')
    weights = {m: importance(groups, edges) for m, (groups, edges) in month_data.items()}
    result = []
    for month, (source, _) in sorted(month_data.items()):
        for horizon in horizons:
            target_month = shift_month(month, horizon)
            window = [shift_month(month, k) for k in range(1, horizon + 1)]
            censored = target_month >= cutoff
            unknown = any(m < cutoff and (m not in month_data or m not in observations or
                observations[m]['records'] == 0 or observations[m].get('empty_corpora')) for m in window)
            available = target_month < cutoff and target_month in month_data and target_month in observations
            observed_through = max([month] + [m for m in window if m < cutoff and m in month_data and m in observations])
            # GED already uses an inverted membership index: no Cartesian join.
            pairs, links = [], {}
            if available:
                target, _ = month_data[target_month]
                links, _, _, pairs = transitions(source, target, weights[month], weights[target_month])
            by_source = defaultdict(list)
            partition = set().union(*month_data[target_month][0].values()) if available else set()
            incoming = Counter(tid for candidates in links.values() for tid, _ in candidates)
            for pair in pairs:
                by_source[pair['source_community_id']].append(pair)
            for cid, members in sorted(source.items()):
                evidence = by_source[cid]
                observed = observations.get(target_month) if available else None
                original = labels.get((month, cid), {})
                row = dict(reference_id=reference, feature_month=month, community_id=cid,
                    feature_available_through_month=month, horizon=horizon,
                    observation_month=target_month,
                    audit_observed_through_month=observed_through,
                    source_size=len(members), size_stratum='le2' if len(members) <= 2 else '3to9' if len(members) < 10 else 'ge10',
                    original_label=original.get('label', '') or 'unresolved',
                    original_reason=original.get('reason', 'no_next_month_reference'),
                    right_censored=censored, coverage_unknown=unknown,
                    observation_status='right_censored' if censored else 'coverage_unknown' if unknown else 'observed',
                    max_inclusion_forward=max((p['inclusion_forward'] for p in evidence), default=0.) if available else None,
                    max_inclusion_backward=max((p['inclusion_backward'] for p in evidence), default=0.) if available else None,
                    strongest_shared_members=max((p['shared_members'] for p in evidence), default=0) if available else None,
                    accepted_matches=len(links.get(cid, [])) if available else None,
                    accepted_merge_candidate=any(incoming[tid] > 1 for tid, _ in links.get(cid, [])) if available else None)
                for channel in ('authored', 'posts', 'comments', 'reply_endpoints'):
                    row[channel + '_fraction'] = len(members & observed[channel]) / len(members) if observed else None
                row['partition_fraction'] = len(members & partition) / len(members) if available else None
                result.append(row)
    return result


def summarize(rows):
    """Keep complete/censored/unknown denominators and original label strata."""
    groups = defaultdict(list)
    for row in rows:
        groups[row['feature_month'], row['community_id']].append(row)
    windows = []
    for key, followup in sorted(groups.items()):
        ordered = sorted(followup, key=lambda r: r['horizon'])
        if [r['horizon'] for r in ordered] != [1, 2, 3]:
            raise ValueError('Every source needs exactly three distinct horizons')
        first, last = ordered[0], ordered[-1]
        if any(r['right_censored'] for r in ordered):
            status = 'right_censored'
        elif any(r['coverage_unknown'] for r in ordered):
            status = 'coverage_unknown'
        elif first['accepted_matches']:
            status = 'accepted_next_month'
        elif any(r['accepted_matches'] for r in ordered[1:]):
            status = 'later_match_candidate'
        else:
            status = 'no_accepted_match_in_observed_window'
        windows.append({k: first[k] for k in ('reference_id', 'feature_month', 'community_id',
            'source_size', 'size_stratum', 'original_label', 'original_reason')} | dict(window_status=status))
    strata = []
    for dimension in ('all', 'feature_month', 'size_stratum', 'original_label', 'original_reason'):
        buckets = defaultdict(list)
        for row in windows:
            buckets['all' if dimension == 'all' else row[dimension]].append(row)
        for value, members in sorted(buckets.items()):
            strata.append(dict(dimension=dimension, value=value, sources=len(members),
                counts=dict(sorted(Counter(r['window_status'] for r in members).items()))))
    return windows, strata
