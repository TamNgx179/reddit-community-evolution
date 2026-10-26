"""Recompute component tables from predictions and draw mechanism comparisons."""

import json
from pathlib import Path

import numpy as np

from reddit_sna.evaluation.components import FULL, definitions, summarize
from reddit_sna.evaluation.temporal_protocol import EVENTS, months
from reddit_sna.pipelines.study_preparation import verified
from reddit_sna.pipelines.study_samples import read_csv


def read_components(root):
    """Verify complete output inventories and recompute every displayed score."""
    root = Path(root)
    verified(root)
    declared = json.loads((root/'declaration.json').read_text(encoding='utf-8'))
    if declared['definitions'] != definitions() or declared['primary_selection'] != 'unchanged':
        raise ValueError('Component declaration differs')
    protocol = declared['protocol']
    result = {}
    for cohort in ('original','external'):
        folder = root/cohort
        verified(folder)
        rows = read_csv(folder/'predictions.csv')
        for row in rows:
            values = np.asarray(json.loads(row['probabilities']),dtype=float)
            if (values.shape != (6,) or not np.isfinite(values).all() or (values < 0).any() or
                not np.isclose(values.sum(),1) or EVENTS[int(values.argmax())] != row['y_pred']):
                raise ValueError('Invalid component probabilities')
        result[cohort] = {phase:summarize([r for r in rows if r['phase']==phase], protocol['seeds'],
            list(definitions()), months(protocol['validation_start'],protocol['test_start']) if phase=='development'
            else months(protocol['test_start'],protocol['end']), protocol['bootstrap_draws'],
            protocol['block_length'],protocol['bootstrap_seed']) for phase in ('development','final')}
        saved = json.loads((folder/'summary.json').read_text(encoding='utf-8'))
        if result[cohort] != saved:
            raise ValueError('Component summary cannot be reproduced')
        checks = json.loads((folder/'reproduction.json').read_text(encoding='utf-8'))
        if any(r['mismatches'] for r in checks.values()) or set(checks) != {FULL,'A1_no_D'}:
            raise ValueError('Historical primary and A1 reproduction is incomplete')
    if result != json.loads((root/'summary.json').read_text(encoding='utf-8')):
        raise ValueError('Combined component summary differs')
    return result


def component_figures(results):
    """Separate cohorts and periods rather than pooling incompatible targets."""
    import matplotlib.pyplot as plt
    figures = {}
    names = list(definitions())
    labels = ['Full','A1 no D','A2 flat matched','No member return','No activity growth',
              'No repeated dyads','No context drift','No observation flags']
    fig, axes = plt.subplots(1,2,figsize=(13,5),layout='constrained')
    for ax,(cohort,data) in zip(axes,results.items()):
        x = np.arange(len(names))
        for offset,phase,color in ((-.18,'development','#4c72b0'),(.18,'final','#c44e52')):
            ax.barh(x+offset,[data[phase]['mean_macro_f1'][n] for n in names],height=.35,
                    color=color,label=phase+' (exposed)')
        ax.set_yticks(x,labels)
        ax.invert_yaxis()
        ax.set(title=cohort.capitalize()+' cohort',xlabel='Fixed six-class Macro-F1')
        ax.grid(axis='x',alpha=.2)
        ax.legend(fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.12),ncol=2)
    fig.suptitle('Controlled component study with identical LR settings')
    figures['components'] = fig
    fig,axes = plt.subplots(1,2,figsize=(13,4.5),layout='constrained',sharey=True)
    for ax,(cohort,data) in zip(axes,results.items()):
        comparisons = data['final']['full_minus_control']
        for index,name in enumerate(names[1:]):
            item = comparisons[name]
            ci = item['ci95']
            ax.plot([ci['low'],ci['high']],[index,index],color='#4c72b0')
            ax.scatter(item['delta'],index,color='#c44e52',zorder=3)
        ax.axvline(0,color='black',linestyle='--',linewidth=.8)
        ax.set_yticks(range(len(names)-1),labels[1:])
        ax.invert_yaxis()
        ax.set(title=cohort.capitalize()+' exposed final',xlabel='Full minus control Macro-F1 with descriptive 95% interval')
        ax.grid(axis='x',alpha=.2)
    figures['paired_differences'] = fig
    return figures


def render_components(results):
    """Describe measured effects without choosing a replacement on exposed final."""
    names = list(definitions())
    rows = '\n'.join('| '+name+' | '+' | '.join(f"{results[c][p]['mean_macro_f1'][name]:.4f}"
        for c,p in (('original','development'),('original','final'),('external','development'),('external','final')))+' |'
        for name in names)
    deltas = []
    for cohort,data in results.items():
        for name,item in data['final']['full_minus_control'].items():
            ci = item['ci95']
            interval = f"[{ci['low']:+.4f}, {ci['high']:+.4f}]" if ci else 'unavailable'
            deltas.append(f"| {cohort} | {name} | {item['delta']:+.4f} | {interval} | {item['months_full_higher']}/{item['months']} |")
    original = results['original']['final']
    external = results['external']['final']
    interpretation = f'''
With settings matched, the two-head model exceeds flat LR by
{original['full_minus_control']['A2_flat_matched']['delta']:+.4f} original and
{external['full_minus_control']['A2_flat_matched']['delta']:+.4f} external Macro-F1.
The original descriptive interval is positive, while the external interval
includes zero. This better isolates organization of the classifier than B3,
whose independently selected hyperparameters differed from the primary.

Removing member-return fields reduces original final Macro-F1 from
{original['mean_macro_f1'][FULL]:.4f} to
{original['mean_macro_f1']['without_member_return']:.4f}, but changes the external
score from {external['mean_macro_f1'][FULL]:.4f} to
{external['mean_macro_f1']['without_member_return']:.4f}. Removing activity-growth
fields instead gives {original['mean_macro_f1']['without_activity_growth']:.4f}
original and {external['mean_macro_f1']['without_activity_growth']:.4f} external.
Thus the nine D fields do not have a uniform benefit. These observations support
a targeted follow-up of behavioral history and coverage rather than treating
all dynamic features as one confirmed mechanism. They do not authorize choosing
a replacement primary from exposed final results.
'''
    return '''## 9. Controlled component evidence

The finite comparison inventory was declared before this supplementary run.
Every configuration uses the primary LR settings (C=1, balanced class weighting,
standard scaling and max_iter=3000), seeds 42/43/44 and the same sample keys.
A2 changes only flat versus two-head organization. A1 removes all nine D fields.
The five grouped deletions remove member-return, activity-growth, repeated-dyad,
context-drift or observation/coverage fields separately. Behavioral deletions
retain the observation flags. The controls are ablations, not extra baselines.

Six expanding development origins cover July to December 2017. Final refits
use data through December 2017 and predict January to September 2018 without
refitting on those outcomes. Both periods were already exposed before this
supplementary study. No new primary is selected from these results.

| Configuration | Original development | Original final | External development | External final |
|---|---:|---:|---:|---:|
'''+rows+'''

Scores are means over three algorithm seeds. Historical full-primary and A1
final predictions were reproduced exactly before interpreting component effects.
The following differences are full minus the named control. Positive values
favor the full configuration. Intervals use the same paired three-month block
resamples for every comparison, 2000 draws and bootstrap seed 2026. These are
descriptive, unadjusted intervals across a finite set of comparisons, not a
new independent confirmation or a causal attribution to social mechanisms.
The six-month development window is too short for the declared minimum of
three block lengths, so its interval is explicitly unavailable.

| Cohort | Control | Full minus control | Descriptive 95% interval | Months full higher |
|---|---|---:|---|---:|
'''+ '\n'.join(deltas)+'\n'+interpretation+'''

The same graph, operational labels and five headline baseline roles remain in
force. Group deletion measures conditional usefulness at fixed settings and can
reflect redundancy between features. Observation flags measure coverage rather
than a social interaction mechanism. Per-class support and monthly predictions
are retained with every configuration. Blinded development cases and blank
review forms are available locally. Verified rule consistency and automated
coverage checks are reported as automation, not completed human assessment.
Both existing cohorts are recorded as exposed. A prospective new-data protocol
specifies source verification, prior-exposure accounting and freezing before
outcome inspection. No new untouched cohort or human agreement is claimed.
'''
