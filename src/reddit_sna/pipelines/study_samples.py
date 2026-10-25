"""Monthly study features, operational targets and explicit censored cases."""

from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path

from reddit_sna.contracts import SnapshotEdge, next_month
from reddit_sna.data.archive import CORPORA, digest_file
from reddit_sna.features.activity import ACTIVITY_FIELDS, DYNAMIC_FIELDS, activity_features
from reddit_sna.features.community import snapshot_features
from reddit_sna.features.context import CONTEXT_FEATURES, context_features
from reddit_sna.features.history import history_features
from reddit_sna.features.lagged import predecessor_features
from reddit_sna.pipelines.study_preparation import seal, verified
from reddit_sna.pipelines.study_resources import json_write
from reddit_sna.tracking.ged import importance, transitions


def read_csv(path):
    with Path(path).open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows, fields=None):
    if fields is None:
        if not rows:
            raise ValueError('Explicit schema required for an empty table')
        fields = list(rows[0])
    with Path(path).open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_month(directory, month):
    """Load only hash-verified canonical memberships and this month's R edges."""
    directory = Path(directory)
    info = verified(directory)
    if info['month'] != month:
        raise ValueError('Month preparation key mismatch')
    groups = defaultdict(set)
    rows = read_csv(directory / f'memberships/{month}/membership-seed0.csv')
    seen = set()
    for row in rows:
        if row['month'] != month or row['user_id'] in seen:
            raise ValueError('Duplicate or inconsistent canonical membership')
        seen.add(row['user_id'])
        groups[row['community_id']].add(row['user_id'])
    edges = [SnapshotEdge(month, r['source_user_id'], r['target_user_id'], float(r['weight']))
             for r in read_csv(directory / f'snapshots/{month}/R.csv')]
    if seen != {u for edge in edges for u in (edge.source_user_id, edge.target_user_id)}:
        raise ValueError('Membership coverage must match reply endpoints')
    return dict(groups), edges


def build_study_samples(database, month_directories, output, reference, cache=None, *, corpora=CORPORA):
    """Rebuild a contiguous cohort; label t only after its t+1 snapshot exists.

    The final snapshot's features remain available but its target is censored.
    Each monthly preparation has an independent cohort hash; the study-level
    reference binds their verified inventory and fixed measurement protocol.
    """
    output = Path(output)
    corpora = tuple(corpora)
    if len(corpora) < 2 or len(set(corpora)) != len(corpora):
        raise ValueError('Samples need a unique declared context cohort')
    ordered = sorted(month_directories)
    if len(ordered) < 2 or any(next_month(a) != b for a,b in zip(ordered, ordered[1:])):
        raise ValueError('Samples require at least two consecutive snapshots')
    # Bind cached normalization to each sealed graph cohort. Older sample
    # manifests lack this field, so their graph inventories remain the evidence.
    for directory in month_directories.values():
        graph = json.loads((Path(directory)/'snapshots.json').read_text(encoding='utf-8'))
        if set(graph['declared_corpora']) != set(corpora):
            raise ValueError('Context corpus normalization differs from graph cohort')
    cached,cache_months,cache_hash={},{},None
    if cache is not None:
        cache=Path(cache)
        info=verified(cache)
        if tuple(info.get('context_corpora', corpora)) != corpora:
            raise ValueError('Cached context normalization differs from declared cohort')
        prefix=info['months']
        if info['stage']!='samples' or info['reference_id']!=reference or prefix!=ordered[:len(prefix)] or len(prefix)>=len(ordered):
            raise ValueError('Feature cache must be a verified strict prefix of this reference cohort')
        for month in prefix:
            if info['input_month_manifests'][month]!=digest_file(Path(month_directories[month])/'complete.json'):
                raise ValueError('Cached feature month differs from the actual graph/membership source')
        cache_months=set(prefix)
        for row in read_csv(cache/'features.csv'):
            key=row['feature_month'],row['community_id']
            if key in cached or key[0] not in cache_months or row['reference_id']!=reference or row['available_through_month']!=key[0]:
                raise ValueError('Invalid cached feature key/cutoff')
            cached[key]={k:v for k,v in row.items() if k not in ('reference_id','feature_month','community_id','available_through_month')}
        cache_hash=digest_file(cache/'complete.json')
    output.mkdir(parents=True, exist_ok=False)
    tracker = dict(method='ged-strength-topology-v1', alpha=.5, beta=.5, dissolve=.1)
    label_ref = hashlib.sha256(json.dumps(dict(reference=reference, **tracker), sort_keys=True).encode()).hexdigest()
    feature_rows, labels, pairs, tracking = [], [], [], []
    features, group_inventory, weight_inventory = {}, {}, {}
    previous, prior_weights, prior_age = None, None, {}
    for index, month in enumerate(ordered):
        print(f'study features: {month}', flush=True)
        groups, edges = load_month(month_directories[month], month)
        weights = importance(groups, edges)
        links = {}
        if previous is not None:
            previous_month = ordered[index - 1]
            links, events, reasons, inclusions = transitions(previous, groups, prior_weights, weights)
            pairs.extend(dict(feature_month=previous_month, label_month=month, **r) for r in inclusions)
            for cid, event in events.items():
                key = dict(reference_id=reference, feature_month=previous_month,
                           community_id=cid, label_month=month, label_reference_id=label_ref)
                labels.append(dict(**key, label=event.value if event else '', eligible=int(event is not None),
                                   reason=reasons[cid], size=len(previous[cid])))
                tracking.extend(dict(**key, target_community_id=target, match_score=value)
                                for target, value in links[cid] or [('', 0.)])
        history = history_features(groups, previous, links, prior_age)
        structural = snapshot_features(groups, edges)
        if month in cache_months:
            if {cid for m,cid in cached if m==month}!=set(groups):
                raise ValueError('Cached community feature inventory differs from membership')
        else:
            context = context_features(database, month, groups, corpora=corpora)
            activity = activity_features(database, month, groups)
        for cid in sorted(groups):
            if month in cache_months:
                values=cached[(month,cid)]
                expected=set(structural[cid])|set(history[cid])|set(CONTEXT_FEATURES)|set(ACTIVITY_FIELDS)|set(DYNAMIC_FIELDS)
                if set(values)!=expected or any(not math.isfinite(float(v)) for v in values.values()):
                    raise ValueError('Cached feature schema/values are invalid')
                if any(float(values[k])!=v for k,v in dict(**structural[cid],**history[cid]).items()):
                    raise ValueError('Cached structure/history differs from recomputed causal evidence')
            else:
                values = dict(**structural[cid], **history[cid], **context[cid], **activity[cid])
            features[(month, cid)] = values
            feature_rows.append(dict(reference_id=reference, feature_month=month, community_id=cid,
                                     available_through_month=month, **values))
        group_inventory[month] = groups
        weight_inventory[month] = weights
        previous, prior_weights = groups, weights
        prior_age = {cid:r['community_age'] for cid,r in history.items()}
    # Explicit censoring makes the last snapshot distinguishable from dissolve.
    last = ordered[-1]
    for cid, users in previous.items():
        labels.append(dict(reference_id=reference, feature_month=last, community_id=cid,
            label_month=next_month(last), label_reference_id=label_ref, label='', eligible=0,
            reason='final_snapshot_censored', size=len(users)))
    lags = predecessor_features(ordered, features,
        [dict(r, eligible=str(r['eligible'])) for r in labels], tracking)
    samples = []
    for row in labels:
        if row['eligible']:
            key = row['feature_month'], row['community_id']
            lag, event = lags[key]
            samples.append(dict(**{k:row[k] for k in ('reference_id','feature_month','community_id','label_month','label_reference_id')},
                **features[key], **lag, past_event=event, label=row['label']))
    write_csv(output / 'samples.csv', samples)
    write_csv(output / 'features.csv', feature_rows)
    write_csv(output / 'labels.csv', labels)
    write_csv(output / 'tracking.csv', tracking, ['reference_id','feature_month','community_id','label_month',
        'label_reference_id','target_community_id','match_score'])
    write_csv(output / 'inclusion_pairs.csv', pairs, ['feature_month','label_month','source_community_id',
        'target_community_id','shared_members','inclusion_forward','inclusion_backward','accepted'])
    from reddit_sna.evaluation.study_labels import audit_labels, prepare_review
    audit = audit_labels(labels, pairs, group_inventory, weight_inventory)
    json_write(output / 'label_audit.json', audit)
    prepare_review(labels, group_inventory, output / 'review', weights=weight_inventory)
    return seal(output, dict(status='complete', stage='samples', reference_id=reference,
        label_reference_id=label_ref, months=ordered, n=len(samples), human_review='pending',
        context_corpora=list(corpora),
        cached_feature_manifest_sha256=cache_hash,
        input_month_manifests={m:digest_file(Path(p) / 'complete.json') for m,p in month_directories.items()}))
