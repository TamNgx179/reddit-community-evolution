"""Independent operational-rule audit and blinded structural-event review packets."""

from collections import Counter, defaultdict
import hashlib
import math
from pathlib import Path
import random

from reddit_sna.pipelines.study_resources import json_write
from reddit_sna.contracts import next_month


def audit_labels(labels, pairs, groups, weights=None):
    """Check target rules independently of the tracker implementation.

    This verifies internal measurement consistency, not social validity. Source
    and target groups must be disjoint partitions within each individual month.
    """
    by_transition = defaultdict(list)
    totals = {}
    ordered=sorted(groups)
    if any(next_month(a)!=b for a,b in zip(ordered,ordered[1:])):
        raise ValueError('Label audit requires consecutive snapshots')
    seen_pairs=set()
    for month, partition in groups.items():
        seen_users=set()
        for cid, members in partition.items():
            if not members or seen_users & members:
                raise ValueError('Audit partitions must be disjoint and nonempty')
            seen_users.update(members)
            if weights is not None:
                values=weights[month][cid]
                if set(values)!=members or any(not math.isfinite(v) or v<=0 for v in values.values()):
                    raise ValueError('Audit importance must cover members with positive finite values')
                totals[(month,cid)]=sum(values.values())
    for pair in pairs:
        f, b = float(pair['inclusion_forward']), float(pair['inclusion_backward'])
        if not (0 <= f <= 1 and 0 <= b <= 1):
            raise ValueError('Invalid inclusion range')
        accepted = f >= .5 or b >= .5 or math.isclose(f,.5,rel_tol=1e-12,abs_tol=1e-12) or math.isclose(b,.5,rel_tol=1e-12,abs_tol=1e-12)
        if int(pair['accepted']) != accepted:
            raise ValueError('Inclusion acceptance rule mismatch')
        m,n,s,t=(pair[k] for k in ('feature_month','label_month','source_community_id','target_community_id'))
        if n!=next_month(m) or (m,n,s,t) in seen_pairs:
            raise ValueError('Duplicate or nonconsecutive inclusion pair')
        seen_pairs.add((m,n,s,t))
        left,right=groups[m][s],groups[n][t]
        common=left & right
        if not common or int(pair['shared_members'])!=len(common):
            raise ValueError('Saved overlap differs from actual membership')
        if weights is not None:
            expected_f=len(common)/len(left)*sum(weights[m][s][u] for u in sorted(common))/totals[(m,s)]
            expected_b=len(common)/len(right)*sum(weights[n][t][u] for u in sorted(common))/totals[(n,t)]
            if not math.isclose(f,expected_f,rel_tol=1e-12,abs_tol=1e-12) or not math.isclose(b,expected_b,rel_tol=1e-12,abs_tol=1e-12):
                raise ValueError('Saved inclusion differs from membership importance')
        by_transition[(pair['feature_month'],pair['label_month'])].append(pair)
    expected_pairs=set()
    for m,n in zip(ordered,ordered[1:]):
        target_owner={u:cid for cid,members in groups[n].items() for u in members}
        for sid,members in groups[m].items():
            expected_pairs.update((m,n,sid,tid) for tid in {target_owner[u] for u in members if u in target_owner})
    if seen_pairs!=expected_pairs:
        raise ValueError('Inclusion inventory must retain every overlapping pair')
    counts, reasons, strata = Counter(), Counter(), Counter()
    seen = set()
    for row in labels:
        m, n, cid = row['feature_month'], row['label_month'], row['community_id']
        if n!=next_month(m) or int(row['size'])!=len(groups[m][cid]):
            raise ValueError('Source label size/month mismatch')
        key = (m,cid)
        if key in seen or cid not in groups[m]:
            raise ValueError('Duplicate or missing source label')
        seen.add(key)
        if n not in groups:
            if row['label'] or int(row['eligible']) or row['reason'] != 'final_snapshot_censored':
                raise ValueError('Final target must be censored')
            reasons[row['reason']] += 1
            continue
        items = by_transition[(m,n)]
        outgoing = [p for p in items if p['source_community_id'] == cid and int(p['accepted'])]
        incoming = Counter(p['target_community_id'] for p in items if int(p['accepted']))
        if not outgoing:
            weak = any(p['source_community_id'] == cid and
                (max(float(p['inclusion_forward']),float(p['inclusion_backward'])) >= .1 or
                 math.isclose(max(float(p['inclusion_forward']),float(p['inclusion_backward'])),.1,rel_tol=1e-12,abs_tol=1e-12)) for p in items)
            expected = '' if weak else 'dissolve'
            reason = 'weak_overlap_unresolved' if weak else 'below_dissolve_threshold'
        elif len(outgoing)>1 and any(incoming[p['target_community_id']]>1 for p in outgoing):
            expected, reason = '', 'many_to_many_unresolved'
        elif len(outgoing)>1:
            expected, reason = 'split', 'multiple_successors'
        elif incoming[outgoing[0]['target_community_id']]>1:
            expected, reason = 'merge', 'multiple_predecessors'
        else:
            difference = len(groups[n][outgoing[0]['target_community_id']]) - len(groups[m][cid])
            expected = 'grow' if difference>0 else 'shrink' if difference<0 else 'stable'
            reason = 'one_to_one_size_comparison'
        if row['label'] != expected or int(row['eligible']) != int(bool(expected)) or row['reason'] != reason:
            raise ValueError('Operational label rule mismatch')
        counts[expected or 'unresolved'] += 1
        reasons[reason] += 1
        size = len(groups[m][cid])
        strata[f'{expected or "unresolved"}:size_{"le2" if size<=2 else "3to9" if size<10 else "ge10"}'] += 1
    expected_keys = {(m,cid) for m,partition in groups.items() for cid in partition}
    if seen != expected_keys:
        raise ValueError('Label inventory must cover every source including censoring')
    return dict(status='automated_rule_consistency_verified', support=dict(counts), reasons=dict(reasons),
        size_strata=dict(strata), human_review='pending',
        target='GED-adapted observed structural events, not social ground truth',
        stable='equal size on accepted one-to-one link; membership may differ',
        dissolve='no meaningful observed inclusion link; not proven social disappearance')


def prepare_review(labels, groups, output, per_stratum=3, seed=42, weights=None):
    """Create two blank reviewer forms and separate answer keys, never annotations."""
    from reddit_sna.pipelines.study_samples import write_csv
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    strata = defaultdict(list)
    for row in labels:
        if row['reason'] != 'final_snapshot_censored':
            strata[row['label'] or row['reason']].append(row)
    rng = random.Random(seed)
    chosen = []
    for _, rows in sorted(strata.items()):
        chosen.extend(rng.sample(sorted(rows, key=lambda r:(r['feature_month'],r['community_id'])),
                                 min(per_stratum,len(rows))))
    rng.shuffle(chosen)
    packets, answers, forms = [], [], []
    for index,row in enumerate(chosen):
        case = f'case-{index+1:04d}'
        source = groups[row['feature_month']][row['community_id']]
        target = {cid:users for cid,users in groups[row['label_month']].items() if users & source}
        union = set().union(*target.values()) if target else set()
        before = {cid:users for cid,users in groups[row['feature_month']].items() if users & union or cid==row['community_id']}
        keys = [row['community_id']] + sorted(set(before)-{row['community_id']})
        token = lambda u:hashlib.sha256(f'{case}:{u}'.encode()).hexdigest()[:24]
        packets.append(dict(case_id=case, feature_month=row['feature_month'], label_month=row['label_month'],
            focal_source='source-0', current_groups={f'source-{i}':sorted(token(u) for u in before[cid]) for i,cid in enumerate(keys)},
            next_groups={f'target-{i}':sorted(token(u) for u in users) for i,(_,users) in enumerate(sorted(target.items()))},
            scope='Observed structural memberships only; no overlap is not proof of social disappearance'))
        if weights is not None:
            packets[-1]['current_importance']={f'source-{i}':{token(u):weights[row['feature_month']][cid][u] for u in sorted(before[cid])}
                                               for i,cid in enumerate(keys)}
            packets[-1]['next_importance']={f'target-{i}':{token(u):weights[row['label_month']][cid][u] for u in sorted(users)}
                                            for i,(cid,users) in enumerate(sorted(target.items()))}
        answers.append(dict(case_id=case, **row))
        forms.extend(dict(case_id=case,reviewer=reviewer,human_label='',confidence='',rationale='')
                     for reviewer in ('reviewer_a','reviewer_b'))
    (output/'reviewer').mkdir()
    (output/'coordinator').mkdir()
    json_write(output/'reviewer/cases.json',packets)
    json_write(output/'coordinator/answers.json',answers)
    write_csv(output/'reviewer/annotations.csv',forms,['case_id','reviewer','human_label','confidence','rationale'])
    json_write(output/'status.json',dict(status='prepared_pending_human_annotation',cases=len(chosen),
        sampling='seeded diagnostic strata; not prevalence representative',
        warning='Coordinator answer key must not be shared with reviewers; folders are not access control'))
