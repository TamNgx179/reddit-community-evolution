"""Separate external-cohort evidence from the original inspected experiment."""

from collections import Counter
import json
from pathlib import Path

from reddit_sna.evaluation.label_validation import coverage_audit
from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.temporal_protocol import COMPACT_MODELS, EVENTS, PRIMARY
from reddit_sna.pipelines.study_preparation import seal, verified
from reddit_sna.pipelines.study_resources import json_write
from reddit_sna.pipelines.study_samples import read_csv
from reddit_sna.pipelines.temporal_study import _attempt, _complete
from reddit_sna.reporting.temporal_study import read_study, study_diagnostics


def read_confirmation(original_root, confirmation_root, review_root):
    """Validate saved predictions and submitted assessments, without refitting."""
    original=read_study(original_root)
    confirmation=read_study(confirmation_root)
    if tuple(confirmation['selection']['models'])!=COMPACT_MODELS:
        raise ValueError('External comparison must retain all seven configurations')
    summaries={}
    for period in ('development','final'):
        source=Path(review_root)/f'{period}-result'
        verified(source)
        summaries[period]=json.loads((source/'summary.json').read_text(encoding='utf-8'))
        original_source=_complete(Path(original_root),'evaluation-samples')
        if summaries[period]['source_manifest_sha256']!=digest_file(original_source/'complete.json'):
            raise ValueError('Review evidence belongs to a different original study')
    source=_complete(Path(confirmation_root),'evaluation-samples')
    coverage=coverage_audit(read_csv(source/'labels.csv'),read_csv(source/'inclusion_pairs.csv'))
    return dict(original=original,confirmation=confirmation,reviews=summaries,coverage=coverage)


def confirmation_figures(data):
    """Three concise figures: within-cohort comparisons, months and support."""
    import matplotlib.pyplot as plt
    import numpy as np
    cohorts=(('Original observed cohort',data['original']),('External political cohort',data['confirmation']))
    fig,axes=plt.subplots(1,2,figsize=(14,5),layout='constrained',sharex=True)
    for ax,(title,cohort) in zip(axes,cohorts):
        scores=cohort['evaluation']['mean_macro_f1']
        names=sorted(COMPACT_MODELS,key=lambda name:scores[name])
        ax.barh(names,[scores[n] for n in names],color=['#c44e52' if n==PRIMARY else '#4c72b0' for n in names])
        ax.set(title=title,xlabel='Fixed six-class Macro-F1');ax.grid(axis='x',alpha=.2)
    fig.suptitle('Compare methods within each cohort; different targets are not pooled')
    result={'comparison':fig}
    fig,axes=plt.subplots(1,2,figsize=(14,4.5),layout='constrained',sharey=True)
    for ax,(title,cohort) in zip(axes,cohorts):
        for name in (PRIMARY,'hier_hgb_dynamic'):
            values=cohort['evaluation']['per_month'][name]
            ax.plot(list(values),list(values.values()),marker='o',label=name)
        ax.set(title=title,ylabel='Fixed six-class Macro-F1');ax.tick_params(axis='x',rotation=45)
        ax.grid(alpha=.2);ax.legend(fontsize=8)
    result['monthly']=fig
    fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained')
    x=np.arange(6)
    for index,(title,cohort) in enumerate(cohorts):
        counts=Counter(r['label'] for r in cohort['samples'] if r['label_month']>='2018-01')
        ax.bar(x+(index-.5)*.35,[counts[e] for e in EVENTS],width=.35,label=title)
    ax.set_xticks(x,EVENTS);ax.set(yscale='symlog',ylabel='Final community transitions (symlog)',title='Actual rare-event support; no duplicated evaluation samples')
    ax.legend();result['support']=fig
    return result


def render_confirmation(data, prefix=''):
    """Explicitly distinguish supplementary automation from human validation."""
    original=data['original']['evaluation'];new=data['confirmation']['evaluation']
    table='\n'.join(f"| {name} | {original['mean_macro_f1'][name]:.4f} | {new['mean_macro_f1'][name]:.4f} |" for name in COMPACT_MODELS)
    counts=[]
    for title,cohort in (('Original',data['original']),('External',data['confirmation'])):
        labels=Counter(r['label'] for r in cohort['samples'] if r['label_month']>='2018-01')
        counts.append(f"| {title} | "+' | '.join(str(labels[e]) for e in EVENTS)+f" | {sum(labels.values())} |")
    review_table='\n'.join(f"| {period} | {value['cases']} | {value['reviewer_type']} | {value['raw_agreement']:.3f} | {value['cohen_kappa'] if value['cohen_kappa'] is not None else 'undefined'} |"
        for period,value in data['reviews'].items())
    champ=new['validation_selected_champion'];interval=new['intervals'].get(champ)
    ci=f"[{interval['low']:+.4f}, {interval['high']:+.4f}]" if interval else 'unavailable'
    final=data['coverage']['periods'].get('final',{})
    near=data['coverage']['near_stability']
    discrepancies='; '.join(f"{period}: {sum(r['first']!=r['machine'] for r in value['discrepancies'])}/{value['cases']} first-assessment and {sum(r['second']!=r['machine'] for r in value['discrepancies'])}/{value['cases']} second-assessment disagreements with the tracker" for period,value in data['reviews'].items())
    return f'''## 10. Target checks and locked external-corpus replication

### 10.1. Structural assessments and provenance

Two separate automated assessments were supplied with blinded structural summaries, without machine labels, model predictions or the other assessment's judgments. The summaries include source/target sizes, all overlapping successor groups, retained-member/importance proportions and up to five largest predecessors per successor. Truncation is disclosed and original membership evidence stays local. The assessment rubric allows unresolved cases rather than forcing agreement with the tracker.

| Panel | Cases | Assessment source | Raw agreement | Unweighted Cohen kappa |
|---|---:|---|---:|---:|
{review_table}

Tracker discrepancies are retained: {discrepancies}. Agreement between assessments does not establish agreement with the operational labeling rule.

These are **supplementary automated checks**, not two independent human annotations, adjudicated truth or social validation. Shared model priors may inflate agreement. Human review remains pending. Disagreements with each other and the tracker are retained; no automatic adjudicator replaces the target labels. The stratified sample is diagnostic and cannot estimate event prevalence. Missing or incomplete submissions cannot produce a completed-review status.

### 10.2. External cohort and fixed design

The separate cohort comprises AustralianPolitics, CanadaPolitics and ukpolitics from the official [ConvoKit catalogue](https://convokit.cornell.edu/documentation/subreddit.html). Corpus names, dates, original selected settings, five baseline roles, proposed method, ablation and uncertainty rules were declared before new forecast labels were prepared. SHA256 and full ZIP CRC identify the acquired archives. This is external-corpus replication; users may overlap and earlier group exposure is uncertified.

Models were refitted using only new-cohort labels before January 2018, with **no new hyperparameter search**. The complete source, protocol, new development samples and fitted models were frozen before preparing January–September 2018 target partitions. The new context entropy denominator is log(3), declared for three corpora; the original log(15) default is preserved. Separate reference IDs prevent pooling different cohort targets.

| Configuration | Original Macro-F1 | External Macro-F1 |
|---|---:|---:|
{table}

The predeclared external comparator is **{champ}**, chosen from prior inspected evidence, not from new final outcomes. Proposed minus that comparator is **{new['delta_vs_champion']:+.4f}**, with 95% paired three-month-block interval **{ci}**. The declared criterion returns **{new['superiority']}**. The strongest realized external baseline is **{new['strongest_realized_baseline']}**, with point difference **{new['delta_vs_strongest']:+.4f}**. Retrospective and external scores describe different targets; compare methods within a cohort rather than claiming a cross-cohort score increase is a model improvement.

![External method comparison]({prefix}comparison.png)

*Figure 8. Separate cohort comparisons. Source: [executed notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

![External monthly comparison]({prefix}monthly.png)

*Figure 9. Temporal replication. Source: [executed notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

### 10.3. Rare classes and unresolved coverage remain measured outcomes

| Final cohort | stable | grow | shrink | merge | split | dissolve | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(counts)}

The external final period has **{final.get('observed_transitions',0)}** transitions with an observed successor, **{final.get('resolved',0)}** with resolvable six-class labels, and **{final.get('labels',{}).get('unresolved',0)}** unresolved. Censored final snapshots are counted separately. Coverage, size strata and every unresolved reason remain in the audited record. No oversampling, small-community exclusion or forced weak-overlap label increases final support.

![Rare-class support]({prefix}support.png)

*Figure 10. Actual final-class counts. Source: [executed notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

Exact-size stability is a restrictive operational definition. Development-only near-stability diagnostics describe alternative 0%, 5% and 10% size tolerances without replacing original labels or choosing a threshold by final Macro-F1. A revised event policy would be a new measurement target requiring separate validation. A larger corpus does not guarantee adequate support for every class; sparse classes and a confidence interval including zero remain explicit limitations.

Among {near['one_to_one_cases']} external development one-to-one transitions, {near['counts']['0.0']} have exactly equal size, {near['counts']['0.05']} differ by at most 5%, and {near['counts']['0.1']} by at most 10%. These nested diagnostic counts are not additional evaluation cases.

The new evidence addresses measurement transparency and replication. It does not by itself establish human target validity, dependable rare-event prediction, universal superiority or paper-level novelty.

'''


def write_confirmation_report(original_root, confirmation_root, review_root):
    """Produce a sealed aggregate supplement, keeping private cases out of it."""
    root=Path(confirmation_root)
    existing=_complete(root,'report-confirmation')
    if existing is not None:return existing
    data=read_confirmation(original_root,root,review_root)
    output=_attempt(root,'report-confirmation');output.mkdir()
    import matplotlib.pyplot as plt
    for name,figure in confirmation_figures(data).items():
        figure.savefig(output/f'{name}.png',dpi=180);plt.close(figure)
    (output/'SUPPLEMENT.md').write_text(render_confirmation(data),encoding='utf-8')
    json_write(output/'summary.json',dict(evaluation=data['confirmation']['evaluation'],coverage=data['coverage'],
        reviews={p:{k:v for k,v in r.items() if k not in ('discrepancies','reviewer_ids','submission_hashes')} for p,r in data['reviews'].items()},
        human_review='pending',independent_users=False))
    seal(output,dict(status='complete',stage='report-confirmation'))
    return output
