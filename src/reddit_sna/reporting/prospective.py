"""Verified prospective-cohort results and concise six-event interpretation."""

import json
from pathlib import Path

import numpy as np

from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.components import summarize
from reddit_sna.evaluation.label_validation import coverage_audit
from reddit_sna.evaluation.temporal_protocol import COMPACT_BASELINES, EVENTS, PRIMARY, months
from reddit_sna.pipelines.prospective import CANDIDATE, FLAT_CONTROL
from reddit_sna.pipelines.study_preparation import verified
from reddit_sna.pipelines.study_samples import read_csv
from reddit_sna.pipelines.temporal_study import _complete
from reddit_sna.reporting.temporal_study import read_study


def read_prospective(root):
    """Recompute metrics from sealed predictions without refitting models.

    Historical readers verify stored source bindings instead of requiring the
    current checkout to remain forever identical to an older experiment.
    """
    root = Path(root)
    data = read_study(root)
    declaration = json.loads((root/'declaration.json').read_text(encoding='utf-8'))
    freeze = json.loads((root/'freeze.json').read_text(encoding='utf-8'))
    acquisition = json.loads((root/'acquisition.json').read_text(encoding='utf-8'))
    if (digest_file(root/'declaration.json') != freeze['declaration_sha256'] or
        acquisition['declaration_sha256'] != digest_file(root/'declaration.json') or
        declaration['declared_utc'] >= acquisition['completed_utc'] or
        acquisition['completed_utc'] >= freeze['frozen_utc'] or
        declaration['primary_fixed'] != CANDIDATE or declaration['candidate_outcome_records_read'] is not False or
        declaration['definitions'] != data['selection']['definitions'] or
        declaration['definitions'] != data['protocol']['definitions']):
        raise ValueError('Prospective declaration/acquisition/fitting chronology differs')
    evaluation = _complete(root,'evaluation')
    info = verified(evaluation)
    if not info['final_targets_prepared_after_freeze'] or info['evaluated_utc'] <= freeze['frozen_utc']:
        raise ValueError('Final outcome chronology is not bound to model freeze')
    protocol = data['protocol']
    predictions = [dict(r,model='full' if r['model']==CANDIDATE else r['model']) for r in data['predictions']]
    contrasts = summarize(predictions,protocol['seeds'],
        ['full' if n==CANDIDATE else n for n in data['selection']['models']],
        months(protocol['test_start'],protocol['end']),protocol['bootstrap_draws'],
        protocol['block_length'],protocol['bootstrap_seed'])
    if contrasts != json.loads((evaluation/'contrasts.json').read_text(encoding='utf-8')):
        raise ValueError('Prospective paired comparisons cannot be reproduced')
    sample_source = _complete(root,'evaluation-samples')
    coverage = coverage_audit(read_csv(sample_source/'labels.csv'),read_csv(sample_source/'inclusion_pairs.csv'))
    data.update(contrasts=contrasts,declaration=declaration,freeze=freeze,acquisition=acquisition,coverage=coverage)
    return data


def prospective_figures(data):
    """Show all baseline roles, rare-event support and month-level behavior."""
    import matplotlib.pyplot as plt
    result = {}
    evaluation = data['evaluation']
    scores = evaluation['mean_macro_f1']
    names = list(data['selection']['models'])
    fig,ax = plt.subplots(figsize=(11,5),layout='constrained')
    colors = ['#c44e52' if n==CANDIDATE else '#4c72b0' if n in COMPACT_BASELINES else '#777777' for n in names]
    ax.barh(names,[scores[n] for n in names],color=colors)
    ax.invert_yaxis()
    ax.set(title='Predeclared new-cohort replication, all configurations retained',xlabel='Fixed six-class Macro-F1')
    ax.grid(axis='x',alpha=.2)
    result['comparison'] = fig
    fig,ax = plt.subplots(figsize=(11,4),layout='constrained')
    monthly = evaluation['per_month']
    for name in (CANDIDATE,PRIMARY,evaluation['strongest_realized_baseline']):
        values = monthly[name]
        ax.plot(list(values),list(values.values()),marker='o',label=name)
    ax.set(title='New-cohort performance across the locked final months',ylabel='Fixed six-class Macro-F1')
    ax.tick_params(axis='x',rotation=45)
    ax.legend(fontsize=8)
    ax.grid(alpha=.2)
    result['monthly'] = fig
    matrix = np.asarray(evaluation['metrics'][f'{CANDIDATE}:42']['confusion'])
    fig,ax = plt.subplots(figsize=(7,6),layout='constrained')
    image = ax.imshow(np.log1p(matrix),cmap='Blues')
    for i in range(6):
        for j in range(6):ax.text(j,i,str(matrix[i,j]),ha='center',va='center',fontsize=9)
    ax.set_xticks(range(6),EVENTS,rotation=45,ha='right')
    ax.set_yticks(range(6),EVENTS)
    ax.set(title='35-field candidate, seed 42, new cohort',xlabel='Predicted event',ylabel='Operational target')
    fig.colorbar(image,ax=ax,label='log(1 + count)')
    result['confusion'] = fig
    return result


def render_prospective(data):
    """Report frozen replication separately from earlier exposed component work."""
    evaluation = data['evaluation']
    scores = evaluation['mean_macro_f1']
    rows = '\n'.join(f'| {name} | {scores[name]:.4f} |' for name in data['selection']['models'])
    strongest = evaluation['strongest_realized_baseline']
    contrast = data['contrasts']['full_minus_control'][strongest]
    ci = contrast['ci95']
    interval = f"[{ci['low']:+.4f}, {ci['high']:+.4f}]" if ci else 'unavailable'
    pruning = data['contrasts']['full_minus_control'][PRIMARY]
    pruning_ci = pruning['ci95']
    pruning_interval = f"[{pruning_ci['low']:+.4f}, {pruning_ci['high']:+.4f}]" if pruning_ci else 'unavailable'
    pre2018 = sum(r['label_month']<'2018-01' for r in data['samples'])
    final = data['coverage']['periods']['final']
    support = evaluation['metrics'][f'{CANDIDATE}:42']['per_class']
    per_class = '\n'.join(f"| {event} | {support[event]['support']} | "+
        ' | '.join(f"{np.mean([evaluation['metrics'][f'{name}:{seed}']['per_class'][event]['f1'] for seed in (42,43,44)]):.4f}"
                   for name in (CANDIDATE,PRIMARY,strongest))+' |' for event in EVENTS)
    return f'''## 10. Predeclared new-cohort replication

### Design and candidate rationale

The supplementary component study motivated a candidate that removes only
record_log_growth and reply_log_growth. It retains 35 of the original 37 fields,
including member-return history, repeated interactions, context drift and
observation indicators. Its two-head LR uses C=1, balanced class weighting and
training-only standard scaling. This candidate and every comparator were fixed
before downloading Anarchism, Libertarian and GreenParty from Cornell.
These corpora had not been used in the recorded project studies. Prior exposure
by other team members is uncertified and users may overlap earlier collections.

Acquisition records observed SHA-256 and ZIP CRC checks. Development metadata,
graphs and labels end before January 2018. Models fit pre-2018 targets and freeze
before January to September 2018 graphs and outcome labels are constructed.
The development prefix is verified unchanged after extension. Graph, Leiden,
GED-adapted label rules and six event order remain consistent with the earlier
study. All methods share one reference, eligible sample set and context schema
inside this cohort. There is no new hyperparameter search or outcome-based
corpus substitution. Raw archives and private assessment cases remain local.

### Measured results

The new collection contributes {pre2018} resolved pre-2018 training transitions
and {final['resolved']} resolved final transitions out of
{final['observed_transitions']} observed final source transitions. Its final
resolved fraction is {final['resolved_fraction']:.2%}. The remaining
{final['labels'].get('unresolved',0)} observed transitions are unresolved and
are not forced into the six classes. There are {final['censored']} separately
censored last-snapshot groups. Raw archive size is an acquisition statistic,
not the number of independent training or evaluation samples.

| Configuration | New-cohort Macro-F1 |
|---|---:|
{rows}

Scores average algorithm seeds 42/43/44. Candidate minus strongest realized
named baseline ({strongest}) is {scores[CANDIDATE]-scores[strongest]:+.4f}, with
descriptive paired 95% interval {interval}, and a higher monthly score in
{contrast['months_full_higher']}/{contrast['months']} months. The primary comparator
was predeclared as dynamic HGB. The realized strongest alternative is identified
after evaluation for transparent reporting. Intervals are unadjusted exploratory
time-block comparisons, not a correction for choosing the strongest after evaluation.
Old final scores are not pooled with this new cohort and no model is replaced
because of the new final outcomes.

Candidate minus the original 37-field hierarchical LR is
{pruning['delta']:+.4f}, with descriptive 95% interval {pruning_interval}.
This direct comparison tests whether removing activity-growth fields transfers
to the new collection, separately from whether either version beats a named
baseline. Both versions and all disagreements remain in the result inventory.

| Event | New-cohort support | Candidate F1 | Original full F1 | Strongest baseline F1 |
|---|---:|---:|---:|---:|
{per_class}

Per-class F1 averages the same three seeds. Support counts transitions once.
Unresolved and censored populations remain in the source audit denominators.
Operational labels describe measured structural continuation, not independent
social ground truth. Technical rule checks and case-based structural assessment
are separate from completed independent human validation.
'''
