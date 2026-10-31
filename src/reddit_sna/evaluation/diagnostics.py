"""Coverage and paired forecast diagnostics, separate from model selection.

Counts refer to community-months. Repeated seeds share the same observations.
Unresolved targets are not converted to dissolve or silently scored as labels.
"""
from collections import Counter, defaultdict
import numpy as np
from reddit_sna.contracts import next_month
from reddit_sna.evaluation.research import KEY, EVENTS, score, matrix_score


def size_band(row):
    n = float(row['size'])
    return '2' if n <= 2 else '3-4' if n <= 4 else '5-20' if n <= 20 else '>20'


def coverage_tables(labels, features, graph=None):
    """Reconcile omitted terminal targets and retain independent denominators."""
    identity = KEY[:3]
    fm = {tuple(r[k] for k in identity): r for r in features}
    lm = {tuple(r[k] for k in identity): r for r in labels}
    if not features or len(fm) != len(features) or len(lm) != len(labels) or set(lm) - set(fm):
        raise ValueError('Coverage requires unique matching feature/label keys')
    last = max(r['feature_month'] for r in features)
    missing = set(fm) - set(lm)
    if any(k[1] != last for k in missing):
        raise ValueError('Only the final snapshot can lack target rows')
    rows = list(labels) + [dict(**{k: fm[key][k] for k in identity}, eligible='0',
                              label='', reason='final_snapshot_censored') for key in sorted(missing)]
    if any(r['available_through_month'] != r['feature_month'] or float(r['size']) <= 0 for r in features):
        raise ValueError('Invalid feature availability or community size')
    result, distributions = [], []
    axes = {'all': lambda f: 'all', 'month': lambda f: f['feature_month'], 'size': size_band,
            'lineage_history': lambda f: 'missing' if float(f['history_missing']) else 'available'}
    for axis, group in axes.items():
        for value in sorted({group(f) for f in features}):
            selected = [r for r in rows if group(fm[tuple(r[k] for k in identity)]) == value]
            censored = [r for r in selected if r['reason'] == 'final_snapshot_censored']
            observed = [r for r in selected if r['reason'] != 'final_snapshot_censored']
            eligible = [r for r in observed if str(r['eligible']) == '1']
            mass = lambda rs: sum(float(fm[tuple(r[k] for k in identity)]['size']) for r in rs)
            record = dict(axis=axis, stratum=value, observed=len(observed), eligible=len(eligible),
                          unresolved=len(observed)-len(eligible), censored=len(censored),
                          coverage=len(eligible)/len(observed) if observed else None,
                          observed_member_months=mass(observed), eligible_member_months=mass(eligible),
                          member_month_coverage=mass(eligible)/mass(observed) if observed else None)
            if graph and axis == 'month':
                g = graph[value]
                if mass(selected) != g['reply_endpoints']:
                    raise ValueError('Community members do not cover the graph endpoints')
                record.update(reply_endpoints=g['reply_endpoints'], observed_users=g['observed_users'],
                              graph_observed_user_coverage=g['reply_coverage_observed_users'],
                              graph_active_author_coverage=g['reply_coverage_active_authors'])
            result.append(record)
            if axis in ('all', 'size'):
                for name, subset in [('eligible', eligible), ('unresolved', [r for r in observed if str(r['eligible']) != '1'])]:
                    for field in ('size', 'density', 'community_age', 'history_missing', 'internal_weight',
                                  'boundary_weight', 'records_per_member_log', 'past_window_fraction', 'context_history_missing'):
                        values = [float(fm[tuple(r[k] for k in identity)][field]) for r in subset
                                  if field in fm[tuple(r[k] for k in identity)]]
                        if values:
                            distributions.append(dict(axis=axis, stratum=value, status=name, field=field, n=len(values),
                                q10=float(np.quantile(values,.1)), median=float(np.median(values)),
                                q90=float(np.quantile(values,.9)), mean=float(np.mean(values))))
    return result, distributions


def prediction_units(predictions):
    """Reject duplicates and any unequal keys or truths within a window."""
    units = defaultdict(dict)
    truths = {}
    for row in predictions:
        key = tuple(row[k] for k in KEY)
        unit = (row.get('window','final'), row['model'], int(row['seed']))
        if (key in units[unit] or row['label_month'] != next_month(row['feature_month'])
                or row['y_true'] not in EVENTS or row['y_pred'] not in EVENTS):
            raise ValueError('Duplicate or invalid prediction key/event')
        if (unit[0],key) in truths and truths[(unit[0],key)] != row['y_true']:
            raise ValueError('Prediction truths differ')
        truths[(unit[0],key)] = row['y_true']
        units[unit][key] = row
    for window in {u[0] for u in units}:
        if len({frozenset(rows) for u,rows in units.items() if u[0]==window}) != 1:
            raise ValueError('Predictions must share full keys within each window')
    return units


def forecast_tables(predictions, features):
    """Fixed-six metrics by month, size and history, with support per seed."""
    units = prediction_units(predictions)
    fm = {tuple(r[k] for k in KEY[:3]):r for r in features}
    metrics, classes, confusion = [], [], []
    for (window,model,seed), rows in sorted(units.items()):
        if any(key[:3] not in fm for key in rows):
            raise ValueError('Prediction lacks a feature row')
        axes = {'all':lambda k:'all', 'month':lambda k:k[3], 'size':lambda k:size_band(fm[k[:3]]),
                'lineage_history':lambda k:'missing' if float(fm[k[:3]]['history_missing']) else 'available',
                'member_activity_history':lambda k:('available' if float(fm[k[:3]].get('context_history_missing',1))==0 else 'missing_or_not_recorded')}
        for axis,group in axes.items():
            for value in sorted({group(k) for k in rows}):
                selected = [r for k,r in rows.items() if group(k)==value]
                s = score(selected)
                base = dict(window=window,model=model,seed=seed,axis=axis,stratum=value)
                metrics.append(dict(**base,n=s['n'],macro_f1_six=s['macro_f1_six'],
                                    accuracy=float(np.trace(s['confusion'])/s['n'])))
                if axis in ('all','month'):
                    matrix = np.asarray(s['confusion'])
                    for i,event in enumerate(EVENTS):
                        support=int(matrix[i].sum()); predicted=int(matrix[:,i].sum())
                        classes.append(dict(**base,label=event,support=support,
                            f1=2*matrix[i,i]/(support+predicted) if support+predicted else 0.,
                            recall=matrix[i,i]/support if support else 0.,to_dissolve=int(matrix[i,EVENTS.index('dissolve')]),
                            predicted=predicted))
                        if axis=='all':
                            confusion.extend(dict(window=window,model=model,seed=seed,truth=event,prediction=p,count=int(matrix[i,j]))
                                             for j,p in enumerate(EVENTS))
    return metrics, classes, confusion


def paired_tables(predictions, features, contrasts, *, draws=1000, block_length=2, bootstrap_seed=20261031):
    """Paired cases and whole-month uncertainty, never treating seeds as samples."""
    units = prediction_units(predictions)
    fm = {tuple(r[k] for k in KEY[:3]):r for r in features}
    cases, intervals = [], []
    for window in sorted({u[0] for u in units}):
        seeds=sorted({u[2] for u in units if u[0]==window})
        for proposed,reference in contrasts:
            if any((window,m,s) not in units for m in (proposed,reference) for s in seeds):
                raise ValueError('Missing paired model/seed')
            for seed in seeds:
                left,right=units[(window,proposed,seed)],units[(window,reference,seed)]
                for key in sorted(left):
                    p,r=left[key],right[key]
                    pc,rc=p['y_pred']==p['y_true'],r['y_pred']==r['y_true']
                    outcome='both_correct' if pc and rc else 'proposed_only' if pc else 'reference_only' if rc else 'both_wrong'
                    f=fm[key[:3]]
                    cases.append(dict(**dict(zip(KEY,key)),window=window,proposed=proposed,reference=reference,seed=seed,
                        y_true=p['y_true'],proposed_prediction=p['y_pred'],reference_prediction=r['y_pred'],outcome=outcome,
                        size=f['size'],size_band=size_band(f),history_missing=f['history_missing']))
            sample=units[(window,proposed,seeds[0])]
            months=sorted({k[3] for k in sample})
            observed=float(np.mean([score(list(units[(window,proposed,s)].values()))['macro_f1_six']-
                                    score(list(units[(window,reference,s)].values()))['macro_f1_six'] for s in seeds]))
            base=dict(window=window,proposed=proposed,reference=reference,delta=observed,months=len(months))
            if len(months)<6:
                intervals.append(dict(**base,low=None,high=None,draws=0,block_length=None,
                                      reason='Fewer than six distinct months'))
                continue
            matrices={}
            for model in (proposed,reference):
                for seed in seeds:
                    for month in months:
                        matrices[(model,seed,month)]=np.asarray(score([r for k,r in units[(window,model,seed)].items() if k[3]==month])['confusion'])
            rng=np.random.default_rng(bootstrap_seed); deltas=[]
            for _ in range(draws):
                starts=rng.integers(0,len(months)-block_length+1,size=-(-len(months)//block_length))
                selected=[months[i+j] for i in starts for j in range(block_length)][:len(months)]
                values=[np.mean([matrix_score(sum(matrices[(m,s,t)] for t in selected))['macro_f1_six'] for s in seeds])
                        for m in (proposed,reference)]
                deltas.append(values[0]-values[1])
            intervals.append(dict(**base,low=float(np.quantile(deltas,.025)),high=float(np.quantile(deltas,.975)),
                                  draws=draws,block_length=block_length,reason='Exploratory paired month blocks'))
    return cases, intervals
