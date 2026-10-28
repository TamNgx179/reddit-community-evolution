"""Matched six-class evaluation and paired monthly-block uncertainty."""

from collections import defaultdict
import numpy as np

from reddit_sna.evaluation.research import EVENTS, KEY, matrix_score, score
from reddit_sna.contracts import next_month


def evaluate_activity_predictions(rows, seeds, models, test_months, proposed, champion, baselines,
                                  draws=2000, block_length=3, bootstrap_seed=2026):
    """Require identical keys/truth for every model; seeds are not time samples."""
    if not rows or proposed not in models or champion not in baselines or not set(baselines)<=set(models):
        raise ValueError('Invalid comparison inventory')
    grouped, keys, truth, monthly = defaultdict(list), defaultdict(set), {}, defaultdict(list)
    for row in rows:
        model, seed = row['model'], int(row['seed'])
        key = tuple(row[k] for k in KEY)
        if not all(isinstance(v,str) and v for v in key) or next_month(row['feature_month'])!=row['label_month']:
            raise ValueError('Invalid community-month prediction key')
        if model not in models or seed not in seeds or row['label_month'] not in test_months:
            raise ValueError('Prediction outside frozen evaluation inventory')
        unit = (model,seed)
        if key in keys[unit]:
            raise ValueError('Duplicate prediction key')
        keys[unit].add(key)
        if key in truth and truth[key] != row['y_true']:
            raise ValueError('Matched model truth mismatch')
        truth[key] = row['y_true']
        grouped[unit].append(row)
        monthly[(model,seed,row['label_month'])].append(row)
    expected = {(model,seed) for model in models for seed in seeds}
    if set(grouped) != expected or any(value != next(iter(keys.values())) for value in keys.values()):
        raise ValueError('Every frozen model/seed must predict the same complete sample cohort')
    if len({(key[0],key[-1]) for key in truth})!=1:
        raise ValueError('Study evaluation cannot mix measurement references')
    if {r['label_month'] for r in rows} != set(test_months):
        raise ValueError('All declared test months must have samples')
    metrics = {f'{name}:{seed}':score(grouped[(name,seed)]) for name,seed in grouped}
    summary = {name:float(np.mean([metrics[f'{name}:{seed}']['macro_f1_six'] for seed in seeds])) for name in models}
    per_month = {name:{month:float(np.mean([score(monthly[(name,seed,month)])['macro_f1_six'] for seed in seeds]))
                       for month in test_months} for name in models}
    strata = {name:{bucket:float(np.mean([score([r for r in grouped[(name,seed)] if
        ('le2' if float(r['size'])<=2 else '3to9' if float(r['size'])<10 else 'ge10')==bucket])['macro_f1_six']
        for seed in seeds])) for bucket in ('le2','3to9','ge10')} for name in models}
    strongest = max(baselines,key=lambda name:summary[name])
    intervals = {}
    if len(test_months) >= 3*block_length:
        matrices = {(model,seed):np.asarray([score(monthly[(model,seed,m)])['confusion'] for m in test_months])
                    for model in models for seed in seeds}
        rng = np.random.default_rng(bootstrap_seed)
        deltas = []
        starts = np.arange(len(test_months)-block_length+1)
        for _ in range(draws):
            selected = np.concatenate([np.arange(s,s+block_length) for s in
                rng.choice(starts,size=int(np.ceil(len(test_months)/block_length)),replace=True)])[:len(test_months)]
            values=[]
            for seed in seeds:
                p=matrix_score(matrices[(proposed,seed)][selected].sum(axis=0))['macro_f1_six']
                b=matrix_score(matrices[(champion,seed)][selected].sum(axis=0))['macro_f1_six']
                values.append(p-b)
            deltas.append(np.mean(values))
        low,high=np.quantile(deltas,[.025,.975]).tolist()
        intervals[champion]=dict(low=low,high=high,draws=draws,block_length=block_length,
                                 scope='paired exploratory monthly blocks; pseudo-label validity separate')
    delta=summary[proposed]-summary[champion]
    beats_all=summary[proposed]>summary[strongest]
    # Matched ablations are displayed controls too. A simpler component control
    # beating the primary contradicts broad superiority even when the named
    # validation-selected baseline is weaker. Do not select a new primary here.
    component_controls=[name for name in models if name.startswith('A_')]
    beats_components=all(summary[proposed]>summary[name] for name in component_controls)
    supported=(delta>=.02 and beats_all and beats_components and champion in intervals and intervals[champion]['low']>0)
    return dict(metrics=metrics,mean_macro_f1=summary,per_month=per_month,size_strata=strata,
        proposed=proposed,validation_selected_champion=champion,strongest_realized_baseline=strongest,
        delta_vs_champion=delta,delta_vs_strongest=summary[proposed]-summary[strongest],
        intervals=intervals,superiority='supported_on_this_operational_target' if supported else 'not_demonstrated',
        beats_all_matched_component_controls=beats_components,
        absent_month_class_policy='fixed six classes, zero_division0',unseen=False,human_review='pending')
