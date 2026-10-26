"""Finite matched component controls and paired temporal uncertainty.

This module defines comparisons before observing their scores. A deletion is
conditional on the fixed model settings and does not prove social causation.
"""

from collections import defaultdict
import json
from pathlib import Path
import tomllib

import numpy as np

from reddit_sna.contracts import next_month
from reddit_sna.evaluation.research import EVENTS, KEY, score
from reddit_sna.evaluation.temporal_protocol import FIELDS

FULL = 'full'
GROUPS = {
    'member_return': ('returning_member_fraction', 'past_active_month_fraction'),
    'activity_growth': ('record_log_growth', 'reply_log_growth'),
    'repeated_dyads': ('repeated_dyad_fraction',),
    'context_drift': ('context_drift_js',),
    'observation_flags': ('past_window_fraction', 'context_history_missing', 'previous_reply_missing'),
}
SETTINGS = dict(estimator='lr', C=1., class_weight='balanced', transform='standard')


def definitions():
    """Keep primary settings and field order fixed for every matched control."""
    result = {FULL: dict(fields=list(FIELDS['dynamic']), hierarchical=True),
              'A1_no_D': dict(fields=list(FIELDS['static']), hierarchical=True),
              'A2_flat_matched': dict(fields=list(FIELDS['dynamic']), hierarchical=False)}
    for group, removed in GROUPS.items():
        result['without_' + group] = dict(
            fields=[f for f in FIELDS['dynamic'] if f not in removed], hierarchical=True)
    return {name: dict(**item, settings=dict(SETTINGS)) for name, item in result.items()}


def load_protocol(path):
    """Reject silent changes to the approved comparison inventory or budget."""
    actual = tomllib.loads(Path(path).read_text(encoding='utf-8'))
    expected = dict(schema_version=1, protocol_id='controlled-components-v1',
        validation_start='2017-07', test_start='2018-01', end='2018-10', seeds=[42,43,44],
        bootstrap_draws=2000, block_length=3, bootstrap_seed=2026,
        working_budget_gib=2, memory_budget_gib=4, minimum_free_gib=2,
        exposure='retrospective_component_analysis_no_new_primary_selection')
    if actual != expected:
        raise ValueError('Unsupported controlled component protocol')
    return actual


def validate_samples(rows):
    """Check source keys, references, finite features and a strict t to t+1 target."""
    if not rows:
        raise ValueError('Nonempty sample table required')
    keys, references = set(), set()
    for row in rows:
        key = tuple(row[k] for k in KEY)
        if not all(isinstance(v, str) and v for v in key) or key in keys:
            raise ValueError('Missing or duplicate sample key')
        if next_month(row['feature_month']) != row['label_month'] or row['label'] not in EVENTS:
            raise ValueError('Invalid source target month or label')
        values = [float(row[f]) for f in FIELDS['dynamic']]
        if not np.isfinite(values).all() or float(row['size']) <= 0:
            raise ValueError('Invalid source features')
        keys.add(key)
        references.add((row['reference_id'], row['label_reference_id']))
    if len(references) != 1:
        raise ValueError('Cannot mix measurement references')


def _macro_batch(matrices):
    """Macro-F1 over a fixed six-class axis for a batch of confusion matrices."""
    tp = np.diagonal(matrices, axis1=-2, axis2=-1)
    denom = matrices.sum(axis=-1) + matrices.sum(axis=-2)
    return np.divide(2 * tp, denom, out=np.zeros_like(tp, dtype=float), where=denom != 0).mean(axis=-1)


def summarize(predictions, seeds, model_names, month_names, draws=2000, block_length=3, bootstrap_seed=2026):
    """Require exact matched keys, then compare full minus each component control.

    Model seeds are averaged within each bootstrap draw. They are not extra
    independent time samples. Intervals are unadjusted descriptive comparisons.
    """
    if (not predictions or not seeds or len(set(seeds)) != len(seeds) or
        not model_names or len(set(model_names)) != len(model_names) or FULL not in model_names or
        not month_names or month_names != sorted(set(month_names)) or
        any(next_month(a) != b for a,b in zip(month_names, month_names[1:])) or
        type(draws) is not int or draws < 1 or type(block_length) is not int or block_length < 1):
        raise ValueError('Invalid component evaluation inventory')
    grouped, monthly, seen, truth = defaultdict(list), defaultdict(list), set(), {}
    for row in predictions:
        model, seed, month = row['model'], int(row['seed']), row['label_month']
        key = tuple(row[k] for k in KEY)
        if (model not in model_names or seed not in seeds or month not in month_names or
            next_month(row['feature_month']) != month or not all(key)):
            raise ValueError('Prediction outside declared inventory')
        identity = (model,seed,key)
        if identity in seen:
            raise ValueError('Duplicate prediction')
        seen.add(identity)
        target = (row['y_true'], float(row['size']))
        if key in truth and truth[key] != target:
            raise ValueError('Mismatched sample truth or size')
        truth[key] = target
        grouped[model,seed].append(row)
        monthly[model,seed,month].append(row)
    if len({(k[0],k[-1]) for k in truth}) != 1:
        raise ValueError('Prediction references differ')
    expected_keys = set(truth)
    for model in model_names:
        for seed in seeds:
            if {tuple(r[k] for k in KEY) for r in grouped[model,seed]} != expected_keys:
                raise ValueError('Incomplete matched prediction set')
            if any(not monthly[model,seed,m] for m in month_names):
                raise ValueError('Missing declared month')
    metrics = {m: {str(s):score(grouped[m,s]) for s in seeds} for m in model_names}
    means = {m:float(np.mean([metrics[m][str(s)]['macro_f1_six'] for s in seeds])) for m in model_names}
    by_month = {m: {t:float(np.mean([score(monthly[m,s,t])['macro_f1_six'] for s in seeds]))
                    for t in month_names} for m in model_names}
    matrices = {m:np.asarray([[score(monthly[m,s,t])['confusion'] for t in month_names]
                            for s in seeds]) for m in model_names}
    intervals = None
    if len(month_names) >= 3 * block_length:
        rng = np.random.default_rng(bootstrap_seed)
        starts = rng.integers(0, len(month_names)-block_length+1,
                              size=(draws, int(np.ceil(len(month_names)/block_length))))
        indices = (starts[...,None] + np.arange(block_length)).reshape(draws,-1)[:,:len(month_names)]
        boot = {m:_macro_batch(matrices[m][:,indices].sum(axis=2)).mean(axis=0) for m in model_names}
        intervals = {m:dict(zip(('low','high'), np.quantile(boot[FULL]-boot[m], [.025,.975]).tolist()))
                     for m in model_names if m != FULL}
    differences = {m:dict(delta=means[FULL]-means[m],
        months_full_higher=sum(by_month[FULL][t]>by_month[m][t] for t in month_names),
        months=len(month_names), ci95=intervals[m] if intervals is not None else None)
        for m in model_names if m != FULL}
    return dict(mean_macro_f1=means, per_seed=metrics, per_month=by_month,
        full_minus_control=differences, samples=len(truth), months=month_names,
        uncertainty=dict(status='available' if intervals is not None else 'insufficient_temporal_blocks',
            draws=draws,block_length=block_length,seed=bootstrap_seed,
            interpretation='paired descriptive unadjusted intervals, not independent confirmation'),
        exposure='retrospective', primary_unchanged=True)
