"""Aggregate charts and an evidence-bound English diagnostic report.

Only completed numeric artifacts are read. Case identities, reviewer answer
keys and fitted pickle objects are neither required nor published here.
"""
from collections import defaultdict
from pathlib import Path
import numpy as np
from reddit_sna.pipelines.controlled_pooling import verify_run
from reddit_sna.pipelines.research import read_table


def read_diagnostics(run):
    """Validate the saved payload before any figure or narrative is produced."""
    run=Path(run).resolve()
    manifest=verify_run(run,run.parents[1])
    return dict(run=run,manifest=manifest,comparison=read_table(run/'comparison.csv'),
        coverage=read_table(run/'replication-coverage.csv'),
        metrics=read_table(run/'replication-metrics.csv'),classes=read_table(run/'replication-classes.csv'),
        intervals=read_table(run/'replication-intervals.csv'))


def build_figures(delivery):
    """Fixed-six-class comparisons with seed spread and explicit denominators."""
    import matplotlib.pyplot as plt
    figures={}
    names=('LR_flat_community','LR_hier_community','LR_flat_member_mean','LR_hier_member_mean',
           'HGB_flat_community','HGB_flat_member_mean','B4_logreg','B5_matched_boosting')
    names+=tuple(n for n in ('HeTCo_v4','A7v4_mean_pool') if any(r['model']==n for r in delivery['comparison']))
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    for ax,window in zip(axes,('main','rolling')):
        rows={r['model']:r for r in delivery['comparison'] if r['window']==window}
        ax.barh(names,[float(rows[n]['macro_f1_six']) for n in names],
                xerr=[float(rows[n]['seed_sd']) for n in names],capsize=3)
        ax.set_xlabel('Six-class Macro-F1, seed mean ± sample SD')
        ax.set_title(window+' — already observed 2016 cohort')
    figures['comparison']=fig
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    monthly=[r for r in delivery['coverage'] if r['axis']=='month' and r['observed']!='0']
    axes[0].plot([r['stratum'] for r in monthly],[float(r['coverage']) for r in monthly],label='Resolved community-months')
    axes[0].plot([r['stratum'] for r in monthly],[float(r['member_month_coverage']) for r in monthly],label='Resolved member-months')
    axes[0].plot([r['stratum'] for r in monthly],[float(r['graph_observed_user_coverage']) for r in monthly],label='Graph / observed user-months')
    axes[0].tick_params(axis='x',rotation=45);axes[0].set_ylim(0,1.05);axes[0].legend(fontsize=8)
    size={r['stratum']:r for r in delivery['coverage'] if r['axis']=='size'}
    bands=[b for b in ('2','3-4','5-20','>20') if b in size]
    axes[1].bar(bands,[float(size[b]['coverage']) for b in bands]);axes[1].set_ylim(0,1)
    axes[1].set_xlabel('Members at feature month');axes[1].set_title('Resolved coverage by size')
    figures['coverage']=fig
    fig,ax=plt.subplots(figsize=(10,4),layout='constrained')
    for model in ('LR_hier_member_mean','LR_hier_community','HGB_flat_member_mean','B4_logreg'):
        values=defaultdict(list)
        for r in delivery['metrics']:
            if r['window']=='rolling' and r['axis']=='month' and r['model']==model:
                values[r['stratum']].append(float(r['macro_f1_six']))
        months=sorted(values)
        ax.plot(months,[np.mean(values[m]) for m in months],marker='o',label=model)
    ax.set_ylabel('Six-class Macro-F1');ax.set_title('Rolling origins, seed means');ax.legend(fontsize=8)
    figures['monthly']=fig
    fig,ax=plt.subplots(figsize=(11,4),layout='constrained')
    labels=('stable','grow','shrink','merge','split','dissolve')
    models=('LR_hier_member_mean','LR_hier_community','HGB_flat_member_mean','B4_logreg')
    x=np.arange(6)
    for i,model in enumerate(models):
        values=defaultdict(list)
        for r in delivery['classes']:
            if r['window']=='main' and r['axis']=='all' and r['model']==model:
                values[r['label']].append(float(r['recall']))
        ax.bar(x+i*.2,[np.mean(values[l]) for l in labels],.2,label=model)
    ax.set_xticks(x+.3,labels);ax.set_ylim(0,1);ax.set_ylabel('Recall, seed mean')
    ax.set_title('Main-window event recall, including zero-support classes');ax.legend(fontsize=8)
    figures['class_recall']=fig
    return figures


def export_figures(run, output):
    """Write only aggregate PNG charts to an explicitly chosen output directory."""
    import matplotlib.pyplot as plt
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    for name,fig in build_figures(read_diagnostics(run)).items():
        fig.savefig(output/f'{name}.png',dpi=160,bbox_inches='tight');plt.close(fig)
    return output


def write_report(run, destination):
    """Describe all configurations and fixed contrasts without choosing a winner."""
    d=read_diagnostics(run);m=d['manifest']
    lines=['# Controlled member-pooling diagnostic study','',
        'This is an exploratory follow-up on an already observed 2016 Reddit cohort. '
        'It preserves the six-event target, graph and tracker. The historical primary and five baseline roles remain unchanged.',
        '', '## Design','',
        'Four LR cells cross flat/hierarchical heads with community-only/community-plus-member means. '
        'Two flat HGB cells use the same two feature sets. Thirteen causal member attributes are averaged within each current community. '
        'Preprocessing is fitted on past training samples only. There is no hyperparameter search.', '',
        f"The completed schedule contains {m['configuration_fits']} configuration fits and {m['internal_heads']} internal heads. "
        f"Measured pipeline wall time is {m['wall_seconds']:.1f} seconds, including feature extraction, fitting and diagnostics. "
        'This is not a separately measured peak-memory result.', '',
        '## Results','', '| Window | Method | Samples per seed | Macro-F1 | Seed SD |',
        '|---|---|---:|---:|---:|']
    for r in d['comparison']:
        lines.append(f"| {r['window']} | {r['model']} | {r['n']} | {float(r['macro_f1_six']):.4f} | {float(r['seed_sd']):.4f} |")
    lines+=['','Each score is the mean of seed-specific fixed-six-class Macro-F1 values. '
        'The seeds repeat the same community-months. Main and rolling windows overlap and are reported separately.',
        '', '## Prespecified contrasts','',
        '| Window | Candidate | Reference | Delta | Month-block interval |', '|---|---|---|---:|---|']
    for r in d['intervals']:
        ci=f"[{float(r['low']):.4f}, {float(r['high']):.4f}]" if r['low'] else 'Unavailable: fewer than six months'
        lines.append(f"| {r['window']} | {r['proposed']} | {r['reference']} | {float(r['delta']):+.4f} | {ci} |")
    lines+=['','The member-feature contrasts keep the estimator and head fixed. The head contrast keeps the member features fixed. '
        'HGB feature controls help test whether any benefit is specific to LR. These are finite diagnostic configurations, not six new headline baselines.',
        '', '## Applicability and error evidence','',
        'Coverage excludes terminal censored targets from its transition denominator and reports unresolved targets separately. '
        'Member-month coverage weights current community size and repeats users across months. Graph observation coverage has a separate denominator.',
        '', '| Scope | Observed | Eligible | Unresolved | Censored | Community coverage | Member coverage |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in d['coverage']:
        if r['axis'] in ('all','size'):
            c=f"{float(r['coverage']):.2%}" if r['coverage'] else 'Undefined'
            mc=f"{float(r['member_month_coverage']):.2%}" if r['member_month_coverage'] else 'Undefined'
            lines.append(f"| {r['axis']}:{r['stratum']} | {r['observed']} | {r['eligible']} | {r['unresolved']} | {r['censored']} | {c} | {mc} |")
    lines+=['','Saved class/month/size/history tables and paired cases expose both directions of disagreement. '
        'Grow/merge predictions of dissolve are final output errors. Those labels alone cannot prove whether the gate or conditional probabilities caused the error.',
        '', '## Interpretation and review status','',
        'The planned diagnostic candidate is LR_hier_member_mean. It is not automatically promoted to replace the historical primary. '
        'All configurations and adverse comparisons remain reported. Deterministic seeds can have zero score variance without establishing generalization stability. '
        'The three-month main window has no month-block confidence interval. Six-month rolling intervals are exploratory and have limited temporal support.',
        '', 'Technical label reconstruction and empty reviewer worksheets do not constitute human validation. '
        'Independent annotation and adjudication remain pending genuine submissions. Results do not establish social ground truth, untouched confirmation or a guaranteed grade.',
        '', '## Reproduction','',
        f"Run directory: `{Path(run).name}`. Read `manifest.json`, `protocol.json`, `cache.json`, `fits.json` and the numeric CSVs. "
        'The completed manifest seals payload hashes and pins source/configuration inputs. Reproduce in a new run directory. '
        'Notebook execution reads these completed outputs and does not refit models.']
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return destination
