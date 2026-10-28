"""Aggregate development observability evidence and archived architecture checks."""

import json
from pathlib import Path

from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.temporal_protocol import PRIMARY
from reddit_sna.pipelines.study_preparation import verified
from reddit_sna.pipelines.study_samples import read_csv
from reddit_sna.pipelines.temporal_study import _complete


def read_audit(path):
    """Read a sealed audit without accessing held-out source periods."""
    path = Path(path)
    info = verified(path)
    if info['stage'] != 'longitudinal-audit' or info['cutoff_exclusive'] != '2018-01':
        raise ValueError('Unsupported longitudinal evidence')
    summary = json.loads((path/'summary.json').read_text(encoding='utf-8'))
    if summary['reference_id'] != info['reference_id']:
        raise ValueError('Mixed audit reference')
    rows = read_csv(path/'horizons.csv')
    windows = read_csv(path/'windows.csv')
    if len(rows) != summary['horizon_rows'] or len(windows) != summary['sources']:
        raise ValueError('Audit denominator mismatch')
    return dict(summary=summary, rows=rows, windows=windows, repeatability=read_csv(path/'repeatability.csv'))


def matched_architecture(study):
    """Separately inspect an archived held-out diagnostic, never select a model.

    This retrospective control is outside the development-only audit. No pickle
    is loaded and no new baseline/model fit is introduced. External replication
    did not save this control, so its unavailability is explicit.
    """
    study = Path(study)
    selection, evaluation = _complete(study, 'selection'), _complete(study, 'evaluation')
    if selection is None:
        raise ValueError('Missing archived selection')
    chosen = json.loads((selection/'selection.json').read_text(encoding='utf-8'))
    freeze = json.loads((study/'freeze.json').read_text(encoding='utf-8'))
    if (Path(study/freeze['selection']).resolve() != selection.resolve() or
            digest_file(selection/'complete.json') != freeze['selection_manifest_sha256']):
        raise ValueError('Architecture diagnostic selection differs from frozen source')
    definitions = chosen['definitions']
    control = 'A_flat_matched'
    if control not in definitions:
        return dict(status='unavailable', reason='No archived matched-flat control in this cohort')
    primary, flat = definitions[PRIMARY], definitions[control]
    if (primary['fields'] != flat['fields'] or primary['settings'] != flat['settings'] or
            primary.get('hierarchical') is not True or flat.get('hierarchical') is not False or
            primary['kind'] != flat['kind']):
        raise ValueError('Archived flat control is not input/setting matched')
    predictions = read_csv(evaluation/'predictions.csv')
    groups = {}
    from reddit_sna.evaluation.research import score
    for name in (PRIMARY, control):
        selected = [r for r in predictions if r['model'] == name]
        keys = [(r['seed'], r['feature_month'], r['community_id']) for r in selected]
        if len(keys) != len(set(keys)) or not selected:
            raise ValueError('Missing/duplicate architecture prediction keys')
        groups[name] = {key: r for key, r in zip(keys, selected)}
    identity = ('reference_id', 'label_reference_id', 'label_month', 'size', 'y_true')
    if groups[PRIMARY].keys() != groups[control].keys() or any(
            any(groups[PRIMARY][k][field] != groups[control][k][field] for field in identity) for k in groups[PRIMARY]):
        raise ValueError('Architecture predictions use different evaluation cases')
    # The established scorer returns the same fixed six-class macro metric.
    values = {}
    for name, group in groups.items():
        seeds = sorted({key[0] for key in group})
        scores = []
        for seed in seeds:
            cases = [r for key, r in sorted(group.items()) if key[0] == seed]
            scores.append(score(cases)['macro_f1_six'])
        values[name] = sum(scores)/len(scores)
    return dict(status='retrospective_auxiliary', macro_f1=values, matched_fields=primary['fields'],
        settings=primary['settings'], prediction_sha256=digest_file(evaluation/'predictions.csv'),
        interpretation='Architecture diagnostic only; not independent confirmation or a sixth baseline')


def audit_figures(cohorts):
    """Three aggregate figures; no user identifiers or individual case exports."""
    import matplotlib.pyplot as plt
    import numpy as np
    states = ('accepted_next_month', 'later_match_candidate', 'no_accepted_match_in_observed_window', 'right_censored', 'coverage_unknown')
    labels = ('Next-month match', 'Later match candidate', 'No accepted match', 'Censored', 'Coverage unknown')
    figures = {}
    fig, ax = plt.subplots(figsize=(10, 4.5), layout='constrained')
    left = np.zeros(len(cohorts))
    for state, label in zip(states, labels):
        counts = [next(s for s in data['summary']['strata'] if s['dimension'] == 'all')['counts'].get(state, 0) for data in cohorts.values()]
        ax.barh(list(cohorts), counts, left=left, label=label)
        left += counts
    ax.set_xlabel('Source communities (all development months, 3-month windows)')
    ax.set_title('Observed continuity is not social survival or death')
    ax.legend(loc='upper center', bbox_to_anchor=(.5, -.2), ncol=3, fontsize=8)
    figures['followup'] = fig
    fig, axes = plt.subplots(1, len(cohorts), figsize=(11, 4), layout='constrained', squeeze=False)
    for ax, (name, data) in zip(axes[0], cohorts.items()):
        rows = [r for r in data['rows'] if r['horizon'] == '1' and r['observation_status'] == 'observed' and r['original_label'] == 'dissolve']
        channels = ('authored_fraction', 'reply_endpoints_fraction', 'partition_fraction')
        values = [sum(float(r[k]) for r in rows)/len(rows) if rows else 0 for k in channels]
        ax.bar(('Authored', 'Reply endpoint', 'Partition'), values)
        ax.set(ylim=(0, 1), title=f'{name}: next-month dissolve (n={len(rows)})', ylabel='Mean within-source member fraction')
        ax.tick_params(axis='x', labelrotation=15)
        if not rows:
            ax.text(.5, .5, 'No observed cases', transform=ax.transAxes, ha='center')
    fig.suptitle('Authorship can remain observable without an accepted community match')
    figures['observation'] = fig
    fig, ax = plt.subplots(figsize=(10, 4), layout='constrained')
    for name, data in cohorts.items():
        rows = data['repeatability']
        months = sorted({r['month'] for r in rows})
        averages = []
        for month in months:
            values = [float(r['ari']) for r in rows if r['month'] == month and r['ari'] != '']
            averages.append(sum(values)/len(values) if values else float('nan'))
        ax.plot(months, averages, marker='.', label=name)
    ax.set_xticks(months[::6])
    ax.set(ylabel='Mean pairwise ARI (defined seed pairs only)', title='Leiden seed repeatability, not ground-truth accuracy', ylim=(-.05, 1.05))
    ax.legend()
    figures['repeatability'] = fig
    return figures


def render_audit(cohorts, architecture, figure_prefix='figures/continuity-001/'):
    """Explain denominators and limitations alongside actual diagnostic counts."""
    lines = ['## 11. Longitudinal observability: what does disappearance mean?', '',
        'A one-month absence is insufficient evidence that a social group has died. '
        'We therefore audited the fixed source membership at t against the independently detected '
        'partitions at t+1, t+2 and t+3. This diagnostic uses only January 2015–December 2017 '
        'development observations in each cohort. No 2018 memberships, final labels or evaluation '
        'stores enter the longitudinal audit. The original six-class labels, features, model '
        'selection and held-out predictions remain unchanged.', '',
        'A candidate match passes the existing weighted GED inclusion threshold in either '
        'direction (0.5). Matching is direct from the same C_t to each later partition, '
        'not an assertion of identity propagated through a lineage. Multiple matches and '
        'merge candidates remain explicit. No accepted match means no observed accepted '
        'membership match in the acquired corpora, **not confirmed social death**.', '',
        '| Development cohort | Source groups | Complete 3-month windows | Next-month match | Later-only candidate | No match in complete window | Censored | Coverage unknown |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name, data in cohorts.items():
        total = next(s for s in data['summary']['strata'] if s['dimension'] == 'all')
        c = total['counts']
        observed = sum(c.get(k, 0) for k in ('accepted_next_month', 'later_match_candidate', 'no_accepted_match_in_observed_window'))
        lines.append(f"| {name} | {total['sources']} | {observed} | {c.get('accepted_next_month', 0)} | {c.get('later_match_candidate', 0)} | {c.get('no_accepted_match_in_observed_window', 0)} | {c.get('right_censored', 0)} | {c.get('coverage_unknown', 0)} |")
    lines += ['', 'For the specific one-month disappearance concern:', '']
    for name, data in cohorts.items():
        mature = [r for r in data['windows'] if r['original_label'] == 'dissolve' and
            r['window_status'] not in ('right_censored', 'coverage_unknown')]
        later = sum(r['window_status'] == 'later_match_candidate' for r in mature)
        lines += [f"- {name}: {later}/{len(mature)} fully observed source groups originally labeled dissolve have a later accepted match candidate at month 2 or 3."]
    lines += ['', 'Complete three-month follow-up requires t no later than September 2017. '
        'Later source groups remain in the censored denominator. A missing month or an acquired '
        'corpus with zero records makes coverage unknown; zero records do not establish absence. '
        'Counts are also retained by month, source size, original label and reason. '
        'These overlapping strata are not additional independent observations.', '',
        f'![Longitudinal follow-up]({figure_prefix}followup.png)', '',
        '*Figure 11. Development follow-up. Source: [executed notebook](../notebooks/core/05_temporal_activity_study.ipynb).*', '',
        '### 11.1. Member activity and network visibility are different', '',
        'Authored activity includes posts and comments written by former members in the target '
        'month. Reply-endpoint observation may include a parent author whose post is older. '
        'Only users incident to a valid reply enter the detected partition. A member can '
        'therefore remain active while lacking an accepted community match. All fractions '
        'use the original source membership as denominator and only the acquired corpus scope.', '',
        '| Cohort | Observed next-month dissolve cases | Mean authored-member fraction | Mean reply-endpoint fraction |',
        '|---|---:|---:|---:|']
    for name, data in cohorts.items():
        rows = [r for r in data['rows'] if r['horizon'] == '1' and r['observation_status'] == 'observed' and r['original_label'] == 'dissolve']
        authored = sum(float(r['authored_fraction']) for r in rows)/len(rows) if rows else None
        endpoints = sum(float(r['reply_endpoints_fraction']) for r in rows)/len(rows) if rows else None
        fmt = lambda value: 'undefined' if value is None else f'{value:.3f}'
        lines.append(f'| {name} | {len(rows)} | {fmt(authored)} | {fmt(endpoints)} |')
    lines += ['', 'These are means across communities, not a pooled unique-user rate. '
        'The observation window and activity-channel distinction qualify the interpretation '
        'of dissolve; they do not automatically relabel any forecast case.', '',
        f'![Member observation]({figure_prefix}observation.png)', '',
        '*Figure 12. Observed member activity. Source: [executed notebook](../notebooks/core/05_temporal_activity_study.ipynb).*', '',
        '### 11.2. Detection repeatability and matched architecture evidence', '',
        'Saved seed0/1/2 partitions were compared on identical monthly node universes and their '
        'pairwise ARI values recomputed. Undefined values remain undefined. Repeatability '
        'measures sensitivity to random initialization, **not accuracy against social ground truth**.', '',
        f'![Detector repeatability]({figure_prefix}repeatability.png)', '',
        '*Figure 13. Leiden seed repeatability. Source: [executed notebook](../notebooks/core/05_temporal_activity_study.ipynb).*', '']
    if architecture['status'] == 'retrospective_auxiliary':
        values = architecture['macro_f1']
        lines += [f"Separately from this development-only audit, an already archived original-cohort held-out matched-flat control scores **{values['A_flat_matched']:.4f}**, versus **{values[PRIMARY]:.4f}** for the hierarchical primary. Feature fields, estimator settings and case keys match; the hierarchy differs. This is a **retrospective auxiliary architecture diagnostic**, not a sixth baseline, a new fit or independent confirmation. The external cohort did not save this matched-flat control, so its architecture comparison is unavailable.", '']
    lines += ['### 11.3. Research decision', '',
        'The prototype currently forecasts **operational next-month structural transitions**. '
        'It does not establish permanent community death or independently validated social labels. '
        'The longitudinal findings constrain interpretation before model improvement: verify '
        'whether gap cases arise from observation loss, changing membership or detector instability. '
        'Human review remains pending. Automated consistency is supplementary.', '',
        'The original primary has the highest point Macro-F1 among the five named baselines '
        'in both cohorts, but the paired interval against the strongest comparator contains zero. '
        'The no-dynamics control also beats the primary in the external cohort. Thus neither '
        'robust superiority nor a general dynamics mechanism has been established. '
        'Do not retune or replace the primary using these final outcomes.', '',
        'If the intended claim is sustained disappearance rather than a next-month transition, '
        'a future target must be versioned with explicit follow-up availability, ambiguous/censored '
        'cases and whole-month train/validation separation that accounts for the longer horizon. '
        'That is a new evaluation task, not a reinterpretation of the existing scores. '
        'The next defensible step is actual human measurement review followed by a separately '
        'declared development design and a new untouched evaluation period.']
    if all('resources' in data for data in cohorts.values()):
        lines += ['', 'Observed audit resources (one-second sampled process-tree RSS; brief peaks may be missed):', '']
        for name, data in cohorts.items():
            resources = data['resources']
            lines += [f"- {name}: {resources['wall_seconds']/60:.2f} minutes, peak sampled RSS {resources['peak_process_tree_rss_bytes']/2**30:.2f} GiB. No new download or model fit was required."]
    return '\n'.join(lines)+'\n'
