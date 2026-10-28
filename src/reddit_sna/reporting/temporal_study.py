"""Portable result verification, scientific figures and one integrated report."""

from collections import Counter
import json
from pathlib import Path

import numpy as np

from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.activity_forecast import evaluate_activity_predictions
from reddit_sna.evaluation.temporal_protocol import COMPACT_BASELINES, COMPACT_MODELS, PRIMARY, EVENTS, months
from reddit_sna.pipelines.study_preparation import seal, verified
from reddit_sna.pipelines.study_resources import json_write
from reddit_sna.pipelines.study_samples import read_csv


def read_study(root):
    """Verify stored predictions/metrics without loading any pickle or raw data.

    Current code need not match a historical experiment to inspect it. The
    archived source and frozen model/config hashes preserve its provenance.
    """
    from reddit_sna.pipelines.temporal_study import _complete
    root=Path(root).resolve()
    freeze=json.loads((root/'freeze.json').read_text(encoding='utf-8'))
    selection=(root/freeze['selection']).resolve()
    if not selection.is_relative_to(root) or digest_file(selection/'complete.json')!=freeze['selection_manifest_sha256']:
        raise ValueError('Frozen selection manifest mismatch')
    verified(selection)
    evaluation=_complete(root,'evaluation')
    source=_complete(root,'evaluation-samples')
    if evaluation is None or source is None:
        raise ValueError('No complete final study evaluation')
    manifest=verified(evaluation)
    if manifest['selection_manifest_sha256']!=digest_file(selection/'complete.json') or manifest['sample_manifest_sha256']!=digest_file(source/'complete.json'):
        raise ValueError('Evaluation source bindings differ')
    protocol=json.loads((root/'protocol.json').read_text(encoding='utf-8'))
    if digest_file(root/'protocol.json')!=freeze['protocol_sha256']:
        raise ValueError('Stored protocol changed after freeze')
    chosen=json.loads((selection/'selection.json').read_text(encoding='utf-8'))
    predictions=read_csv(evaluation/'predictions.csv')
    samples=read_csv(source/'samples.csv')
    expected={(r['reference_id'],r['feature_month'],r['community_id'],r['label_month'],r['label_reference_id']):r
              for r in samples if r['label_month']>=protocol['test_start']}
    if len(expected)!=sum(r['label_month']>=protocol['test_start'] for r in samples):
        raise ValueError('Duplicate final sample key')
    for row in predictions:
        key=tuple(row[k] for k in ('reference_id','feature_month','community_id','label_month','label_reference_id'))
        if key not in expected or expected[key]['label']!=row['y_true'] or expected[key]['size']!=row['size']:
            raise ValueError('Saved predictions differ from the frozen sample target/size')
        probabilities=json.loads(row['probabilities'])
        if chosen['definitions'][row['model']]['kind']!='legacy':
            values=np.asarray(probabilities,dtype=float)
            if values.shape!=(6,) or not np.isfinite(values).all() or (values<0).any() or not np.isclose(values.sum(),1) or EVENTS[int(values.argmax())]!=row['y_pred']:
                raise ValueError('Saved probabilities do not reproduce the event prediction')
    if len(predictions)!=len(expected)*len(chosen['models'])*len(protocol['seeds']):
        raise ValueError('Incomplete study prediction inventory')
    actual=evaluate_activity_predictions(predictions,protocol['seeds'],chosen['models'],
        months(protocol['test_start'],protocol['end']),chosen['proposed'],chosen['champion'],chosen['baselines'],
        protocol['bootstrap_draws'],protocol['block_length'],protocol['bootstrap_seed'])
    saved=json.loads((evaluation/'evaluation.json').read_text(encoding='utf-8'))
    if json.dumps(actual,sort_keys=True)!=json.dumps(saved,sort_keys=True):
        raise ValueError('Saved evaluation cannot be reproduced from predictions')
    audit=json.loads((source/'label_audit.json').read_text(encoding='utf-8'))
    inputs=json.loads((source/'complete.json').read_text(encoding='utf-8'))['input_month_manifests']
    graph_scale=[]
    for month in months(protocol['start'],protocol['end']):
        prepared=_complete(root,f'month-{month}')
        if prepared is None or digest_file(prepared/'complete.json')!=inputs[month]:
            raise ValueError('Graph figure source differs from the evaluated cohort')
        graph_scale.append(json.loads((prepared/'snapshots.json').read_text(encoding='utf-8'))['months'][0])
    first=_complete(root,f'month-{protocol["start"]}')
    membership=read_csv(first/f'memberships/{protocol["start"]}/membership-seed0.csv')
    owners={r['user_id']:r['community_id'] for r in membership}
    sizes=Counter(owners.values())
    top=sorted(sizes,key=lambda cid:(-sizes[cid],cid))[:20]
    between=Counter()
    for edge in read_csv(first/f'snapshots/{protocol["start"]}/R.csv'):
        u,v=owners[edge['source_user_id']],owners[edge['target_user_id']]
        if u!=v and u in top and v in top:
            between[tuple(sorted((u,v)))]+=float(edge['weight'])
    corpora=json.loads((first/'snapshots.json').read_text(encoding='utf-8'))['declared_corpora']
    resources=[json.loads(p.read_text(encoding='utf-8')) for p in (root/'resources').glob('*.json')]
    completed=[r for r in resources if r['status']=='complete']
    measurement_path=_complete(root,'measurement')
    measurement=(json.loads((measurement_path/'measurement.json').read_text(encoding='utf-8'))
                 if measurement_path else None)
    return dict(root=root,protocol=protocol,selection=chosen,evaluation=actual,samples=samples,
                predictions=predictions,label_audit=audit,exposure=freeze['exposure'],graph_scale=graph_scale,
                quotient=dict(month=protocol['start'],nodes=top,sizes=dict(sizes),edges=dict(between)),
                resources=dict(completed_phases=len(completed),
                    summed_completed_phase_seconds=sum(r['wall_seconds'] for r in completed),
                    max_sampled_rss_bytes=max((r['peak_process_tree_rss_bytes'] for r in completed),default=0)),
                measurement=measurement,corpora=corpora)


def read_compact_study(root):
    """Audit the complete original run before presenting five baselines and two research configurations.

    Older broad results stay immutable. This is a role-based projection after
    evaluation, never a new untouched test or a replacement of the old winner.
    Refuse a projection that would hide the preselected primary, validation
    champion, or strongest originally evaluated named baseline.
    """
    data=read_study(root)
    original=data['evaluation']
    if original['proposed']!=PRIMARY or not set(COMPACT_MODELS)<=set(data['selection']['models']):
        raise ValueError('Compact view must preserve the original primary and required controls')
    for key in ('validation_selected_champion','strongest_realized_baseline'):
        if original[key] not in COMPACT_BASELINES:
            raise ValueError('Compact view would omit a stronger original baseline or selected champion')
    predictions=[r for r in data['predictions'] if r['model'] in COMPACT_MODELS]
    protocol=data['protocol']
    compact=evaluate_activity_predictions(predictions,protocol['seeds'],COMPACT_MODELS,
        months(protocol['test_start'],protocol['end']),PRIMARY,original['validation_selected_champion'],
        COMPACT_BASELINES,protocol['bootstrap_draws'],protocol['block_length'],protocol['bootstrap_seed'])
    if compact['mean_macro_f1'][PRIMARY]!=original['mean_macro_f1'][PRIMARY] or compact['intervals']!=original['intervals']:
        raise ValueError('Presentation must not change primary predictions or paired uncertainty')
    selection=dict(data['selection'])
    selection.update(models=list(COMPACT_MODELS),baselines=list(COMPACT_BASELINES),
        definitions={n:selection['definitions'][n] for n in COMPACT_MODELS})
    data.update(selection=selection,evaluation=compact,predictions=predictions,
        presentation=dict(original_model_count=len(original['mean_macro_f1']),
            displayed_model_count=len(COMPACT_MODELS),post_evaluation_projection=len(original['mean_macro_f1'])>len(COMPACT_MODELS),
            full_original_results_retained=True))
    return data


def study_figures(data):
    """Return publication-readable comparison/support/trajectory/confusion figures."""
    import matplotlib.pyplot as plt
    results=data['evaluation']
    proposed=results['proposed']
    names=sorted(results['mean_macro_f1'],key=results['mean_macro_f1'].get)
    fig,ax=plt.subplots(figsize=(10,max(3.5,.42*len(names)+1)),layout='constrained')
    ax.barh(names,[results['mean_macro_f1'][n] for n in names],
            color=['#c44e52' if n==proposed else '#4c72b0' for n in names])
    ax.set(xlabel='Fixed six-class Macro-F1 (mean over estimator seeds)',title='Frozen chronological evaluation')
    ax.grid(axis='x',alpha=.2)
    figures={'comparison':fig}
    fig,ax=plt.subplots(figsize=(10,4.8),layout='constrained')
    for name in dict.fromkeys((proposed,results['validation_selected_champion'],results['strongest_realized_baseline'])):
        values=results['per_month'][name]
        ax.plot(list(values),list(values.values()),marker='o',label=name)
    ax.tick_params(axis='x',rotation=30)
    ax.set(ylabel='Fixed six-class Macro-F1',title='Month-by-month generalization')
    ax.legend(fontsize=8)
    ax.grid(alpha=.2)
    figures['monthly']=fig
    fig,ax=plt.subplots(figsize=(8,5),layout='constrained')
    periods=(('train','2015-02','2017-07'),('validation','2017-07','2018-01'),('test','2018-01','2018-10'))
    for i,(name,start,end) in enumerate(periods):
        counts=Counter(r['label'] for r in data['samples'] if start<=r['label_month']<end)
        ax.bar(np.arange(6)+(i-1)*.25,[counts[e] for e in EVENTS],width=.25,label=name)
    ax.set_xticks(np.arange(6),EVENTS)
    ax.set(yscale='symlog',ylabel='Community transitions (symlog scale)',title='Operational label support; all classes retained')
    ax.legend()
    figures['support']=fig
    fig,ax=plt.subplots(figsize=(7.5,6),layout='constrained')
    matrix=np.asarray(results['metrics'][f'{proposed}:42']['confusion'])
    image=ax.imshow(np.log1p(matrix),cmap='Blues')
    for i in range(6):
        for j in range(6):
            ax.text(j,i,str(matrix[i,j]),ha='center',va='center',fontsize=9)
    ax.set_xticks(range(6),EVENTS,rotation=35)
    ax.set_yticks(range(6),EVENTS)
    ax.set(xlabel='Predicted event',ylabel='Operational reference',title='Proposed confusion matrix (seed42; log color)')
    fig.colorbar(image,ax=ax,label='log(1 + count)')
    figures['confusion']=fig
    fig,ax=plt.subplots(figsize=(11,3),layout='constrained')
    ax.set_xlim(0,11);ax.set_ylim(0,3);ax.axis('off')
    boxes=[(0.1,'Observed replies\nthrough month t'),(2.4,'Weighted user graph\nR(u,v)=wuv+wvu'),
           (4.8,'Leiden community\n+ past activity'),(7.2,'Frozen forecaster\nno future features'),(9.3,'Event forecast\nfor t+1')]
    for x,label in boxes:
        ax.text(x,1.5,label,ha='left',va='center',fontsize=9,bbox=dict(boxstyle='round,pad=.5',fc='#edf2fa'))
    for x in (2,4.4,6.8,9):
        ax.annotate('',xy=(x+.25,1.5),xytext=(x,1.5),arrowprops=dict(arrowstyle='->'))
    ax.set_title('System flow schematic; not an empirical network visualization')
    figures['flow']=fig
    fig,axes=plt.subplots(2,1,figsize=(11,6),sharex=True,layout='constrained')
    scale=data['graph_scale']
    x=np.arange(len(scale))
    axes[0].plot(x,[r['reply_endpoints'] for r in scale],label='Users incident to valid replies')
    axes[0].plot(x,[r['undirected_edges'] for r in scale],label='Unique weighted undirected edges')
    axes[0].set(ylabel='Count',title='Observed monthly reply-network scale')
    axes[0].legend(fontsize=8)
    axes[1].plot(x,[r['reply_coverage_active_authors'] for r in scale],color='#55a868')
    axes[1].set(ylabel='Active-author edge coverage',ylim=(0,1.05))
    ticks=x[::3]
    axes[1].set_xticks(ticks,[scale[i]['month'] for i in ticks],rotation=45)
    for ax in axes:ax.grid(alpha=.2)
    figures['graph_scale']=fig
    fig,ax=plt.subplots(figsize=(8,7),layout='constrained')
    quotient=data['quotient'];nodes=quotient['nodes']
    angles=np.linspace(0,2*np.pi,len(nodes),endpoint=False)
    positions={cid:np.array([np.cos(angle),np.sin(angle)]) for cid,angle in zip(nodes,angles)}
    for (u,v),weight in sorted(quotient['edges'].items(),key=lambda item:(-item[1],item[0]))[:40]:
        xy=np.stack((positions[u],positions[v]))
        ax.plot(xy[:,0],xy[:,1],color='#777777',alpha=.35,linewidth=.5+np.log1p(weight)/2,zorder=1)
    for index,cid in enumerate(nodes):
        xy=positions[cid]
        ax.scatter(*xy,s=60+100*np.log1p(quotient['sizes'][cid]),color=plt.get_cmap('tab20')(index%20),
                   edgecolor='white',zorder=2)
        ax.text(*xy,str(index+1),ha='center',va='center',fontsize=9,zorder=3)
    ax.set_title(f"Empirical community interaction graph: {quotient['month']}")
    ax.set(xlim=(-1.3,1.3),ylim=(-1.3,1.3),aspect='equal')
    ax.axis('off')
    fig.text(.5,.02,'Largest up to20 Leiden communities; top up to40 between-community reply links.\n'
        'Node area uses log community size; edge width uses log reply weight. Display filter only.',
        ha='center',fontsize=8)
    figures['community_graph']=fig
    return figures


def study_diagnostics(data):
    """Describe the frozen predictions; never select or refit a model.

    The original validation champion remains the primary comparison. The added
    nonlinear dynamic reference is explicitly a retrospective secondary contrast.
    Its interval must not be confused with the original champion interval.
    """
    result=data['evaluation'];protocol=data['protocol']
    strongest=result['strongest_realized_baseline']
    secondary=evaluate_activity_predictions(data['predictions'],protocol['seeds'],
        data['selection']['models'],months(protocol['test_start'],protocol['end']),
        result['proposed'],strongest,data['selection']['baselines'],
        protocol['bootstrap_draws'],protocol['block_length'],protocol['bootstrap_seed'])
    seeds=protocol['seeds'];events=tuple(EVENTS);primary=result['proposed']
    # Pooling months for F1 is distinct from averaging month-level F1. Estimator
    # seed repetitions have the same targets and are not independent data units.
    per_class={}
    for name in (primary,strongest):
        matrices=[np.asarray(result['metrics'][f'{name}:{seed}']['confusion']) for seed in seeds]
        support=matrices[0].sum(axis=1)
        values=[]
        for matrix in matrices:
            denominator=matrix.sum(axis=0)+matrix.sum(axis=1)
            values.append(np.divide(2*np.diag(matrix),denominator,
                out=np.zeros(6,dtype=float),where=denominator!=0))
        per_class[name]=[dict(label=e,support=int(support[i]),f1=float(np.mean(values,axis=0)[i]))
                         for i,e in enumerate(events)]
    wins=sum(result['per_month'][primary][m]>result['per_month'][strongest][m]
             for m in result['per_month'][primary])
    return dict(strongest_reference=strongest,
        secondary_interval=secondary['intervals'].get(strongest),
        secondary_superiority=secondary['superiority'],per_class=per_class,
        monthly_wins_against_strongest=wins,months=len(result['per_month'][primary]),
        analysis='retrospective descriptive comparison; no refit or new independent test')


def render_study_report(data, figure_prefix=''):
    """Write an evidence-led English midterm narrative from verified run data."""
    result=data['evaluation'];diagnostic=study_diagnostics(data)
    primary=result['proposed'];champion=result['validation_selected_champion']
    strongest=result['strongest_realized_baseline'];scores=result['mean_macro_f1']
    periods=(('Training','2015-02','2017-07'),('Validation','2017-07','2018-01'),
             ('Final evaluation','2018-01','2018-10'))
    supports={name:Counter(r['label'] for r in data['samples'] if start<=r['label_month']<end)
              for name,start,end in periods}
    support_table='\n'.join(f'| {name} | '+ ' | '.join(str(c[e]) for e in EVENTS)+f' | {sum(c.values()):,} |'
                            for name,c in supports.items())
    roles={'B1_majority':('B1 Majority','Most frequent training label; minimum sanity check'),
           'B1_persistence':('B2 Persistence','Known predecessor event; training-majority fallback'),
           'flat_lr_dynamic':('B3 Flat LR + dynamics','Same full inputs, direct six-class prediction; tests hierarchy'),
           'hier_hgb_static':('B4 Hierarchical HGB static','Strong original validation champion; already includes current activity'),
           'hier_hgb_dynamic':('B5 Hierarchical HGB + dynamics','Same full inputs and hierarchy; strong nonlinear reference'),
           'hier_lr_dynamic':('Proposed hierarchical LR + dynamics','Two-stage linear forecast with interpretable past-activity features'),
           'A_no_dynamics_matched':('Ablation: proposed without D','Same selected primary settings, removing dynamic features only')}
    score_table='\n'.join(f'| {roles[n][0]} | {scores[n]:.4f} | {roles[n][1]} |'
                          for n in data['selection']['models'])
    class_table='\n'.join(f"| {row['label']} | {row['support']} | {row['f1']:.4f} | {other['f1']:.4f} |"
        for row,other in zip(diagnostic['per_class'][primary],diagnostic['per_class'][strongest]))
    size_table='\n'.join(f"| {label} | {result['size_strata'][primary][key]:.4f} | {result['size_strata'][strongest][key]:.4f} |"
        for key,label in [('le2','2 or fewer members'),('3to9','3–9 members'),('ge10','10 or more members')])
    audit=data['label_audit'];unresolved=audit['support'].get('unresolved',0)
    transitions=sum(audit['support'].values());coverage=(transitions-unresolved)/transitions if transitions else 0
    graph=data['graph_scale'];nodes=[r['reply_endpoints'] for r in graph];edges=[r['undirected_edges'] for r in graph]
    comment_count=sum(r['comment_records'] for r in graph)
    test=supports['Final evaluation'];test_n=sum(test.values());dissolve_share=test.get('dissolve',0)/test_n if test_n else 0
    interval=result['intervals'].get(champion);secondary=diagnostic['secondary_interval']
    def ci(value):
        return f"[{value['low']:+.4f}, {value['high']:+.4f}]" if value else 'not estimable from this run'
    measured=data['measurement'];sensitivity='Measurement diagnostics are unavailable in this run.'
    if measured:
        rates=[]
        for threshold in (.4,.6):
            rows=[r for r in measured['thresholds'] if r['alpha']==threshold]
            changed=sum(r['changed_from_primary'] for r in rows);total=sum(r['source_communities'] for r in rows)
            rates.append(f"threshold {threshold}: {changed}/{total:,} changed source-transition labels")
        resolution=', '.join(f"gamma={r['gamma']}: ARI={r['ari_against_gamma1']:.3f}" for r in measured['resolutions'])
        sensitivity='; '.join(rates)+'. On the measured development graph, '+resolution+'.'
    settings=data['selection']['definitions'][primary]['settings']
    primary_setting=', '.join(f'{k}={v}' for k,v in settings.items())
    image=lambda name:figure_prefix+name+'.png'
    presentation=data.get('presentation',{})
    provenance=('The submitted seven-configuration view is a retrospective reduction of a completed broader study. '
        'The original primary, predictions, validation champion and full archived results are retained. '
        'HGB dynamic was an alternative architecture in that study and is now explicitly treated as a strong nonlinear reference. '
        'This role change is disclosed; it is not a new preregistered comparison or an independent rerun.'
        if presentation.get('post_evaluation_projection') else
        'This run uses the declared seven-configuration protocol. Exposure to previously inspected outcomes remains documented separately.')
    return f'''# Forecasting Structural Evolution of Reddit User Communities

**Midterm research report**

## Executive summary

We implemented an end-to-end prototype that converts observed Reddit replies into monthly user networks, detects communities, derives structural evolution labels and forecasts each existing community's next-month event. The research question is whether past member activity and sustained interaction add predictive value beyond current structure and activity, and whether a two-stage forecast helps with the highly imbalanced event distribution.

The verified run contains **{len(graph)} monthly snapshots**, **{sum(supports['Training'].values()):,} training**, **{sum(supports['Validation'].values()):,} validation** and **{test_n:,} final-evaluation community–month samples**. The frozen proposed model scores **{scores[primary]:.4f} six-class Macro-F1** versus **{scores[strongest]:.4f}** for the strongest of the five reported baselines. This is a preliminary improvement on an algorithm-derived structural target, not proof of accurate social-community prediction. Rare events and unresolved transitions remain central limitations.

## 1. Problem, motivation and research questions

The unit of interest is a **community of interacting users detected in a network**, rather than a subreddit, post or individual account. At the end of month t, can information already available predict whether that community will retain its size, grow, shrink, merge, split or lose meaningful observed continuity in t+1? This directly addresses temporal community evolution in SNA. The intended use is monitoring observed community continuity; the system does not infer political affiliation, social intent or causal mechanisms.

- **RQ1 — Dynamic information:** Do returning-member activity and sustained replies add value beyond structure, predecessor history, subreddit context and current activity?
- **RQ2 — Forecast architecture:** Does separating observed disappearance from the other events outperform a direct classifier with the same features?
- **RQ3 — Robustness:** Where does improvement hold across months, classes and community sizes, and how sensitive is the measurement to graph/label choices?

The working hypothesis is that equally large and dense communities may differ in repeated participation and interaction persistence. These measurable differences motivate the features; they do not guarantee better forecasts.

## 2. Exact task: input, output and information boundary

**Raw input:** utterance ID, author pseudonym, parent-reply ID, conversation/thread ID, subreddit and UTC timestamp from the ConvoKit Reddit corpus [1], [2], [7]. Text and eventual popularity are not required for the proposed activity features.

**Model input:** one community C_t detected at the end of t, its current weighted reply structure, predecessor information already known at t, and member activity/replies in t and up to three earlier observed months. Historical activity is computed on the fixed current member set C_t. No t+1 memberships, replies or target labels enter a forecast feature.

**Output:** a six-element probability vector and its highest-probability event for C_t at t+1. At evaluation time, the forecast is compared against the structural label derived after observing t+1. Probabilities have not been established as calibrated. Future graph observations are used to construct evaluation targets, never as prediction inputs.

![System flow]({image('flow')})

*Figure 1. Forecasting pipeline. Source: [executed study notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

## 3. Dataset and feasibility

The observed collection comprises **{len(data['corpora'])} subreddit corpora**: {', '.join(data['corpora'])}. This is a topic-biased observational collection, not a representative sample of all Reddit. A user can participate in several subreddits; a subreddit is an activity context, not a ground-truth community label. The source documentation also warns that incomplete thread histories and duplicate processing entries can occur [1]. Our normalizer deduplicates record IDs, rejects inconsistent duplicates and records graph losses.

Across the study snapshots there are **{comment_count:,} comment records** before graph-event exclusions, **{min(nodes):,}–{max(nodes):,} monthly reply endpoints**, and **{min(edges):,}–{max(edges):,} unique undirected edges per month**. Comment records, account endpoints, edges and labeled community–months are different units; their counts must not be conflated. Parent records may predate the first study month and are retained for reply resolution rather than treated as extra forecast samples.

| Label-month partition | stable | grow | shrink | merge | split | dissolve | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
{support_table}

Metadata are streamed into an indexed local store and graphs are processed month by month. We do not generate a quadratic clique among all users in a thread. Runtime stops enforce the declared 30 GiB working budget, 8 GiB sampled process-tree RSS ceiling and 12 GiB minimum free disk. The maximum RSS recorded in completed phases is **{data['resources']['max_sampled_rss_bytes']/2**30:.2f} GiB**; one-second monitoring can miss brief peaks. These measurements support feasibility on the observed collection, not unlimited scaling.

## 4. Network construction before forecasting

1. For each valid reply written in UTC month t, add a directed interaction from its author u to the parent author v. The parent timestamp must not exceed the reply timestamp. Count repeated replies as weight.
2. Exclude self-replies, invalid authors, missing parents and temporally invalid links from graph edges, recording the exclusions and coverage. Loss incidence counters may overlap and should not be summed as disjoint records.
3. Detect communities on the weighted undirected projection **R_t(u,v)=w_t(u,v)+w_t(v,u)**. A node is a pseudonymous account incident to a valid reply; accounts without a valid edge are counted separately.
4. Run independent weighted Leiden with the RB objective, resolution gamma=1 and canonical seed0 [3]. Seeds1/2 are measurement diagnostics, not additional independent datasets. Communities are detected independently each month and linked afterward.

![Network scale]({image('graph_scale')})

*Figure 2. Monthly network scale and reply coverage. Source: [study notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

![Observed community network]({image('community_graph')})

*Figure 3. Observed community interaction graph. Source: [study notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

Figure 3 is a quotient graph of up to the twenty largest detected communities, showing up to forty strongest between-community reply links. The display filter does not remove communities, edges or samples from the experiment. It illustrates the measured network, not an independent validation of social groups.

## 5. Labels: definition, generation and validity

Reddit supplies **no native community-evolution class labels**. We create **GED-adapted operational pseudo-labels** using consecutive detected partitions [4]. For source A and successor B, weighted inclusion is

$$I(A,B)=\\frac{{|A\\cap B|}}{{|A|}}\\frac{{\\sum_{{u\\in A\\cap B}}q_A(u)}}{{\\sum_{{u\\in A}}q_A(u)}}.$$

Here q_A(u) is internal weighted degree, replaced by 1 if zero. A link is accepted if either directional inclusion reaches 0.5. This is our documented adaptation, not a claim to reproduce every original GED rule.

| Target | Exact operational rule |
|---|---|
| split | More than one accepted successor, without a many-to-many conflict |
| merge | One accepted successor with more than one accepted predecessor |
| grow / shrink / stable | One-to-one link; successor size is larger / smaller / equal |
| dissolve | No accepted link and no overlap with directional inclusion reaching 0.1 |
| unresolved, excluded from classification | Weak-overlap ambiguity or a many-to-many conflict |
| censored, not a class | Last snapshot has no observed successor month |

**Worked example, synthetic:** if two equally important four-person groups share three members, each directional inclusion is(3/4)×(3/4)=0.5625. A one-to-one link receives `stable` because sizes match, even though a member changed. Thus stable means equal observed size, not unchanged membership. Dissolve means loss of sufficient observed inclusion, not verified social disappearance. Forming is outside this source-community task because a newly born future community has no existing C_t to forecast from.

The audit records **{transitions:,} source transitions with an observed next snapshot**, including **{unresolved:,} unresolved ({1-coverage:.2%})**. Classification results therefore apply to the **{coverage:.2%}** with resolvable labels, not all detected transitions. Missing data, monthly aggregation and detector resolution may influence labels. Automated recomputation checks rule consistency; two-person blinded review forms exist, but **human annotation and agreement are still pending**. The labels are suitable for a clearly bounded structural forecasting experiment; their social validity remains unestablished.

Development-only sensitivity: {sensitivity} These checks do not retune the forecast target or demonstrate robustness under every network construction. In particular, resolution sensitivity remains a limitation.

## 6. Evaluation plan and why each experiment exists

Training label months are February 2015–June 2017. Six expanding validation origins cover July–December 2017; each fit uses only earlier labels. After choosing settings, models are refitted through December 2017 and frozen before evaluating January–September 2018. Scalers and class weights learn only from training folds. There is no random row split and no model refitting on final labels [5].

**Primary metric:** Macro-F1 with a fixed six-class list and zero_division=0. We retain absent/rare classes in the metric and report per-class F1/support, confusion, monthly and size-stratum results. All methods predict identical sample keys, targets and dates. Three estimator seeds measure algorithm variability, not independent temporal replications.

| Experiment | Scientific purpose |
|---|---|
| B1 Majority and B2 Persistence | Establish frequency and temporal-repeatability reference levels |
| B3 Flat LR, same full features | Isolate the hierarchy comparison within a linear model family |
| B4 Hierarchical HGB static | Compare with the original strong champion already given current activity |
| B5 Hierarchical HGB dynamic | Test whether the proposed advantage survives a nonlinear model with the same full inputs |
| Proposed without D, settings fixed | Check the contribution of activity/interaction dynamics |
| Class, month, size and measurement diagnostics | Identify where the aggregate improvement does and does not hold |

The compact forward protocol has **five baselines, one proposed model and one ablation**. Four tuned families receive eight configurations and the same six origins: **192 configuration–fold evaluations**. Two-head configurations fit up to two estimators per evaluation, so192 is not a count of individual head fits. Majority/Persistence have fixed rules; the ablation reuses selected primary settings. This replaces the original480 configuration–fold design without adding new test-driven searches.

{provenance}

The original validation champion remains **{champion}**. A paired moving-block bootstrap uses three-month blocks,2,000 draws and a fixed seed, following the time-block resampling principle [8], with pooled confusion matrices and mean-over-seed F1 differences. The nine-month interval is exploratory. We additionally compute the same descriptive contrast against the stronger expanded reference, clearly distinguishing it from the original frozen primary comparison. Past post-2015 outcome exposure has not been independently certified; the chronology alone does not establish an untouched confirmation set.

## 7. Proposed method and relation to prior work

Feature groups are **S**(current structure), **H**(community history), **L**(known predecessor state), **C**(subreddit activity context), **A**(current member activity/replies) and **D**(past activity and interaction dynamics). Static uses S+H+L+C+A; dynamic adds D. D includes returning-member fraction, observed active-month fraction, log changes in records and internal replies, repeated dyads and subreddit-distribution drift. Empty or missing histories carry explicit flags; missing observations are not proof of inactivity.

The proposed **hierarchical Logistic Regression with dynamics** first predicts P(dissolve). A second Logistic Regression predicts the other five classes conditional on non-dissolution. Composition uses P(event)=(1−P(dissolve))P(event|non-dissolve), with an explicit dissolve probability and fixed-class argmax. Single-class or empty-conditional training folds use documented training-only fallbacks. The selected primary setting is **{primary_setting}**; model outputs are not claimed to be calibrated.

The two-stage design is motivated by a common disappearance event and heterogeneous surviving-community transitions. It is still evaluated against the same-input flat LR and nonlinear hierarchical controls, rather than assumed to help. The no-D ablation fixes selected primary settings; it measures that fitted design's dependence on D, not the best possible independently retuned static LR.

GED provides the structural-event framework [4]. Prior work already predicts community evolution from historical states [6]. We therefore claim an implemented and measured activity/interaction feature design on this observed Reddit task, **not invention of community-evolution prediction, a complete HeTCo implementation, or established methodological novelty**. More complex representation models are future comparators, not methods already reproduced here.

## 8. Measured results and interpretation

| Method | Six-class Macro-F1, mean of three seeds | Why it is included |
|---|---:|---|
{score_table}

The frozen proposed model exceeds the strongest reported baseline **{strongest}** by **{result['delta_vs_strongest']:+.4f}**. Against the original validation champion, its difference is **{result['delta_vs_champion']:+.4f}**, with 95% paired interval **{ci(interval)}**. The secondary strongest-reference interval is **{ci(secondary)}**; its automatic descriptive criterion is **{diagnostic['secondary_superiority']}**. A higher point estimate alone must not be described as confirmed superiority if this interval includes zero. These are preliminary observed-cohort results with rule-derived labels.

![Method comparison]({image('comparison')})

*Figure 4. Five baselines, proposed and ablation. Source: [executed study notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

![Monthly results]({image('monthly')})

*Figure 5. Monthly generalization. Source: [study notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

The proposed method wins **{diagnostic['monthly_wins_against_strongest']}/{diagnostic['months']}** observed months against the strongest expanded reference. It is not uniformly superior over time.

### 8.1. Rare classes and errors

| Event | Final support | Proposed F1, mean seeds | Strongest-reference F1, mean seeds |
|---|---:|---:|---:|
{class_table}

Dissolve accounts for **{dissolve_share:.2%}** of final samples. Stable has only **{test.get('stable',0)}** final cases. The headline metric must therefore be read with the class table: the current system cannot be presented as reliably forecasting all six events. Better aggregate performance does not resolve rare-class validity or guarantee useful forecasts for growth/stability.

![Class support]({image('support')})

*Figure 6. Class support by temporal split. Source: [study notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

![Proposed confusion]({image('confusion')})

*Figure 7. Proposed confusion matrix, seed42. Source: [study notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

### 8.2. Component and size diagnostics

Removing D at fixed settings changes Macro-F1 from **{scores[primary]:.4f}** to **{scores['A_no_dynamics_matched']:.4f}**. Same-input flat LR achieves **{scores['flat_lr_dynamic']:.4f}**. These contrasts support investigating activity dynamics and hierarchy on this cohort; they do not establish social causality or a separately significance-tested contribution for every component.

| Source-community size | Proposed Macro-F1 | Strongest-reference Macro-F1 |
|---|---:|---:|
{size_table}

Each size bucket retains the fixed six-class metric, so class absence and composition affect its score. Size-stratum results are descriptive, not independent validation datasets. No small-community exclusion was introduced to improve the headline result.

## 9. Prototype, reproducibility and midterm status

The runnable path is **raw archives → normalized metadata → monthly graphs → Leiden partitions → audited event labels → causal features → temporal selection/freeze → prediction/evaluation → report/notebook**. The CLI stages are normalize-development, develop, select, evaluate and report. Completed stages carry hashes; incomplete/failed attempts are retained, and verified completed months can be resumed. The evaluation gate rejects source/config/model drift after selection. Historical run readers validate saved targets, probability vectors and metrics without loading model pickles.

The [executed notebook](../notebooks/core/05_temporal_activity_study.ipynb) contains code, saved metric output and all seven figures. [README](../README.md) and the [runbook](../docs/RUNBOOK.md) document environment and execution. A fresh checkout needs the documented raw data/environment and either a completed local run or an explicit new run; saved GitHub notebook output is a static evidence snapshot, not a hosted executable service.

| Midterm requirement | Evidence and status |
|---|---|
| Detailed experimental plan | RQs, exact task, five baseline roles, tuning budgets, split/metric/uncertainty rules in this report and runtime protocol |
| Baseline results | Five methods evaluated on identical frozen community–month targets |
| Preliminary proposed results | Selected two-stage LR, actual scores, probabilities and per-class errors |
| Basic comparison | Strongest-reference, original champion, ablation, temporal and size analysis |
| Prototype demonstration | End-to-end CLI, resumable artifacts and executed seven-figure notebook |

**Next work, prioritized by scientific risk:** independently review a blinded sample spanning all event classes and unresolved cases, report agreement/adjudication and investigate detector/target errors; establish a new genuinely unexposed confirmation cohort before further model selection; examine rare-event support and monthly-resolution sensitivity on development data; then evaluate additional architectures only against the same audited task. Any change to label semantics or eligibility creates a new versioned target and requires a new evaluation, not a replacement of these results.

The midterm demonstrates a functioning research prototype and interpretable preliminary evidence. Human target validity, rare-event reliability, unseen confirmation and novelty remain incomplete. Improving the report cannot substitute for those experiments or justify a guaranteed grade.

## References

[1] CornellNLP, “Reddit Corpus (by subreddit),” ConvoKit documentation. [Online]. Available: [corpus documentation](https://convokit.cornell.edu/documentation/subreddit.html).

[2] J. Baumgartner et al., “The Pushshift Reddit Dataset,” Proceedings of ICWSM, vol.14, pp.830–839,2020. [doi:10.1609/icwsm.v14i1.7347](https://doi.org/10.1609/icwsm.v14i1.7347).

[3] V. A. Traag, L. Waltman, and N. J. van Eck, “From Louvain to Leiden: Guaranteeing well-connected communities,” Scientific Reports, vol.9, Art.5233,2019. [doi:10.1038/s41598-019-41695-z](https://doi.org/10.1038/s41598-019-41695-z).

[4] P. Bródka, S. Saganowski, and P. Kazienko, “GED: The method for group evolution discovery in social networks,” Social Network Analysis and Mining, vol.3, pp.1–14,2013. [doi:10.1007/s13278-012-0058-8](https://doi.org/10.1007/s13278-012-0058-8).

[5] Scikit-learn developers, “Cross-validation: Evaluating estimator performance.” [Online]. Available: [documentation](https://scikit-learn.org/stable/modules/cross_validation.html).

[6] S. Saganowski et al., “Predicting Community Evolution in Social Networks,” Entropy, vol.17, pp.3053–3096,2015. [doi:10.3390/e17053053](https://doi.org/10.3390/e17053053).

[7] J. P. Chang et al., “ConvoKit: A Toolkit for the Analysis of Conversations,” Proceedings of SIGDIAL,2020. [Paper](https://www.cs.cornell.edu/~cristian/ConvoKit_Demo_Paper_files/convokit-demo-paper.pdf).

[8] H. R. Künsch, “The Jackknife and the Bootstrap for General Stationary Observations,” The Annals of Statistics, vol.17, no.3, pp.1217–1241,1989. [doi:10.1214/aos/1176347265](https://doi.org/10.1214/aos/1176347265).
'''


def write_study_report(root):
    """Generate a versioned English report; preserve prior sealed report stages."""
    from reddit_sna.pipelines.temporal_study import _attempt, _complete
    root=Path(root)
    if _complete(root,'report-midterm-v3') is not None:
        return
    data=read_compact_study(root)
    output=_attempt(root,'report-midterm-v3');output.mkdir()
    import matplotlib.pyplot as plt
    for name,figure in study_figures(data).items():
        figure.savefig(output/f'{name}.png',dpi=180)
        plt.close(figure)
    (output/'MIDTERM_REPORT.md').write_text(render_study_report(data),encoding='utf-8')
    json_write(output/'diagnostics.json',study_diagnostics(data))
    seal(output,dict(status='complete',stage='report-midterm-v3',models=data['selection']['models'],
        language='en',historical_projection=data['presentation']))
