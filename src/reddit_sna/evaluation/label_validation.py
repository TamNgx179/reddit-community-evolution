"""Blinded structural assessments and honest coverage/annotation accounting.

Automated assessments are supplementary evidence, never independent human
validation or social ground truth. Source artifacts, judgments and coordinator
keys remain local. Stratified review panels cannot estimate event prevalence.
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import random

import numpy as np

from reddit_sna.contracts import Event
from reddit_sna.data.archive import digest_file
from reddit_sna.pipelines.study_samples import load_month, read_csv, write_csv
from reddit_sna.pipelines.study_preparation import seal, verified
from reddit_sna.pipelines.study_resources import json_write
from reddit_sna.pipelines.temporal_study import _complete
from reddit_sna.tracking.ged import importance

LABELS = tuple(event.value for event in Event) + ('unresolved',)
CONFIDENCE = ('low','medium','high')


def coverage_audit(labels, pairs=()):
    """Retain unresolved/censored denominators and development-only sensitivity."""
    periods = defaultdict(lambda:dict(labels=Counter(),reasons=Counter(),sizes=Counter(),censored=0))
    monthly = defaultdict(lambda:dict(labels=Counter(),reasons=Counter(),sizes=Counter(),censored=0))
    seen = set()
    for row in labels:
        key=(row['feature_month'],row['community_id'])
        if key in seen:raise ValueError('Duplicate source transition')
        seen.add(key)
        period=('train' if row['label_month']<'2017-07' else
                'validation' if row['label_month']<'2018-01' else 'final')
        result=periods[period]
        if row['reason']=='final_snapshot_censored':
            result['censored']+=1
            monthly[row['label_month']]['censored']+=1
            continue
        label=row['label'] or 'unresolved'
        if label not in LABELS:raise ValueError('Unknown structural event')
        result['labels'][label]+=1;result['reasons'][row['reason']]+=1
        size=int(row['size']);bucket='le2' if size<=2 else '3to9' if size<10 else 'ge10'
        result['sizes'][f'{label}:{bucket}']+=1
        monthly[row['label_month']]['labels'][label]+=1
        monthly[row['label_month']]['reasons'][row['reason']]+=1
        monthly[row['label_month']]['sizes'][f'{label}:{bucket}']+=1
    output={}
    for period,result in periods.items():
        total=sum(result['labels'].values());unresolved=result['labels']['unresolved']
        output[period]=dict(**result,observed_transitions=total,
            resolved=total-unresolved,resolved_fraction=(total-unresolved)/total if total else None)
    # These are alternative operational targets, never replacement test labels.
    sizes={(r['feature_month'],r['community_id']):int(r['size']) for r in labels}
    accepted=defaultdict(list)
    for pair in pairs:
        if int(pair['accepted']):accepted[(pair['feature_month'],pair['source_community_id'])].append(pair)
    changes=[]
    for row in labels:
        if row['label_month']>='2018-01' or row['reason']!='one_to_one_size_comparison':continue
        outgoing=accepted[(row['feature_month'],row['community_id'])]
        if len(outgoing)!=1:raise ValueError('One-to-one source lacks its accepted link')
        target=sizes.get((row['label_month'],outgoing[0]['target_community_id']))
        if target is not None:changes.append(abs(target-int(row['size']))/int(row['size']))
    return dict(periods=output,monthly=dict(sorted(monthly.items())),human_review='pending',
        near_stability=dict(scope='development-only descriptive alternative targets; original labels unchanged',
            one_to_one_cases=len(changes),counts={str(t):sum(v<=t for v in changes) for t in (0.,.05,.1)}),
        claim='Resolved-case performance does not describe all observed transitions')


def prepare_panel(study_root, output, period, per_stratum=5, seed=2026):
    """Create private source-bound panels with no machine labels in rater data.

    Compact summaries expose sizes, all overlaps, retention and predecessor
    topology. Full membership lists and internal-degree evidence are retained
    only in the coordinator store. Folder separation is not access control;
    distribute only the individual reviewer files.
    """
    root=Path(study_root).resolve();output=Path(output).resolve()
    if period not in ('development','final') or type(per_stratum) is not int or per_stratum<1:
        raise ValueError('Known period and positive per-stratum count required')
    if output==root or output.is_relative_to(root):raise ValueError('Panel must not modify a study')
    if output.exists():raise FileExistsError('Preserve existing review panel')
    source=_complete(root,'evaluation-samples')
    if source is None:raise ValueError('A complete measured cohort is required')
    labels=read_csv(source/'labels.csv');strata=defaultdict(list)
    for row in labels:
        if row['reason']=='final_snapshot_censored':continue
        if (row['label_month']<'2018-01') != (period=='development'):continue
        strata[row['label'] or row['reason']].append(row)
    rng=random.Random(seed);chosen=[]
    for name,rows in sorted(strata.items()):
        ordered=sorted(rows,key=lambda r:(r['feature_month'],r['community_id']))
        chosen.extend((name,row) for row in rng.sample(ordered,min(per_stratum,len(ordered))))
    rng.shuffle(chosen)
    if not chosen:raise ValueError('No reviewable transitions in this period')
    cache={}
    for month in sorted({r[k] for _,r in chosen for k in ('feature_month','label_month')}):
        groups,edges=load_month(_complete(root,f'month-{month}'),month)
        cache[month]=(groups,importance(groups,edges))
    cases=[];answers=[]
    for index,(stratum,row) in enumerate(chosen):
        case=f'{period}-{index+1:04d}'
        before,left=cache[row['feature_month']];after,right=cache[row['label_month']]
        members=before[row['community_id']];targets=[]
        for target,users in sorted(after.items()):
            common=members & users
            if not common:continue
            predecessors=[]
            for origin,previous in sorted(before.items()):
                overlap=len(previous & users)
                if overlap:
                    predecessors.append(dict(focal=origin==row['community_id'],size=len(previous),shared=overlap))
            ordered=sorted(predecessors,key=lambda p:-p['shared'])
            targets.append(dict(target=f'target-{len(targets)+1}',size=len(users),shared=len(common),
                source_retained=len(common)/len(members),target_from_source=len(common)/len(users),
                source_importance_retained=sum(left[row['community_id']][u] for u in sorted(common))/sum(left[row['community_id']].values()),
                target_importance_from_source=sum(right[target][u] for u in sorted(common))/sum(right[target].values()),
                overlapping_predecessor_count=len(predecessors),
                largest_other_predecessor_share=max((p['shared']/len(users) for p in predecessors if not p['focal']),default=0),
                predecessors=ordered[:5],predecessor_display_limit=5))
        cases.append(dict(case_id=case,feature_month=row['feature_month'],label_month=row['label_month'],
            source_size=len(members),targets=targets,
            scope='Observed structural continuation; no overlap does not prove social disappearance'))
        answers.append(dict(case_id=case,stratum=stratum,**row))
    (output/'reviewer').mkdir(parents=True);(output/'coordinator').mkdir()
    json_write(output/'reviewer/cases.json',cases)
    for role in ('assessment_1','assessment_2'):
        write_csv(output/f'reviewer/{role}.csv',[dict(case_id=c['case_id'],label='',confidence='',rationale='') for c in cases])
    json_write(output/'coordinator/answers.json',answers)
    json_write(output/'coordinator/coverage.json',coverage_audit(labels,read_csv(source/'inclusion_pairs.csv')))
    manifest=dict(status='prepared_pending_assessments',period=period,cases=len(cases),
        seed=seed,per_stratum=per_stratum,strata=dict(Counter(a['stratum'] for a in answers)),
        source_manifest_sha256=digest_file(source/'complete.json'),
        payload_sha256=digest_file(output/'reviewer/cases.json'),human_review='pending',
        sampling='diagnostic stratified panel, not prevalence representative')
    json_write(output/'manifest.json',manifest)
    seal(output,dict(status='complete',stage='review-panel'))
    return manifest


def _submission(path, cases, payload_hash):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    required=('reviewer_id','reviewer_type','provenance','payload_sha256','submitted_utc','attestations','judgments')
    if any(k not in data for k in required):raise ValueError('Submission lacks provenance')
    if data['reviewer_type'] not in ('human','automated') or not data['reviewer_id'] or not data['provenance']:
        raise ValueError('Actual reviewer type and identity are required')
    if data['payload_sha256']!=payload_hash:raise ValueError('Judgments belong to a different panel')
    try:
        timestamp = datetime.fromisoformat(data['submitted_utc'].replace('Z','+00:00'))
        if timestamp.tzinfo is None:raise ValueError('Timezone required')
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError('A real timezone-aware submission timestamp is required') from error
    for key in ('answer_key_not_seen','predictions_not_seen','other_assessment_not_seen'):
        if data['attestations'].get(key) is not True:raise ValueError('Blinding attestation missing')
    indexed={}
    for row in data['judgments']:
        key=row.get('case_id')
        if key not in cases or key in indexed:raise ValueError('Duplicate/unknown review case')
        if row.get('label') not in LABELS or row.get('confidence') not in CONFIDENCE or not row.get('rationale','').strip():
            raise ValueError('Each judgment needs a label, confidence and rationale')
        indexed[key]=row
    if set(indexed)!=set(cases):raise ValueError('Partial/blank submissions cannot certify completed review')
    return data,indexed


def summarize_panel(panel, first, second, output, adjudication=None):
    """Compute agreement from real submitted records without inventing gold labels."""
    panel=Path(panel).resolve();output=Path(output).resolve()
    if output==panel or output.is_relative_to(panel):raise ValueError('Preserve original review panel')
    if output.exists():raise FileExistsError('Preserve previous review results')
    verified(panel)
    manifest=json.loads((panel/'manifest.json').read_text(encoding='utf-8'))
    payload=panel/'reviewer/cases.json'
    if digest_file(payload)!=manifest['payload_sha256']:raise ValueError('Review payload changed')
    cases={r['case_id'] for r in json.loads(payload.read_text(encoding='utf-8'))}
    if not cases or len(cases)!=manifest['cases']:raise ValueError('Empty or duplicated panel cases')
    a,ia=_submission(first,cases,manifest['payload_sha256'])
    b,ib=_submission(second,cases,manifest['payload_sha256'])
    if a['reviewer_id']==b['reviewer_id']:raise ValueError('One identity is not two reviewers')
    if a['reviewer_type']!=b['reviewer_type']:raise ValueError('Report human and automated assessments separately')
    matrix=np.zeros((7,7),dtype=int)
    for key in sorted(cases):matrix[LABELS.index(ia[key]['label']),LABELS.index(ib[key]['label'])]+=1
    n=int(matrix.sum());observed=float(np.trace(matrix)/n)
    chance=float(matrix.sum(axis=0)@matrix.sum(axis=1)/n**2)
    kappa=(observed-chance)/(1-chance) if chance<1 else None
    answers=json.loads((panel/'coordinator/answers.json').read_text(encoding='utf-8'))
    discrepancies=[]
    for row in answers:
        machine=row['label'] or 'unresolved';key=row['case_id']
        discrepancies.append(dict(case_id=key,machine=machine,first=ia[key]['label'],second=ib[key]['label'],
            raters_agree=ia[key]['label']==ib[key]['label'],stratum=row['stratum']))
    human=a['reviewer_type']=='human'
    adjudicated=None
    if adjudication is not None:
        record=json.loads(Path(adjudication).read_text(encoding='utf-8'))
        if (record.get('reviewer_id') in (None,'',a['reviewer_id'],b['reviewer_id']) or
            record.get('reviewer_type')!=a['reviewer_type'] or
            not record.get('provenance') or not record.get('submitted_utc') or
            record.get('payload_sha256')!=manifest['payload_sha256']):
            raise ValueError('Adjudication requires separate actual provenance and the same panel')
        expected={key for key in cases if ia[key]['label']!=ib[key]['label']}
        outcomes={}
        for row in record.get('judgments',[]):
            key=row.get('case_id')
            if key not in expected or key in outcomes or row.get('label') not in LABELS or not row.get('rationale','').strip():
                raise ValueError('Invalid or fabricated adjudication inventory')
            outcomes[key]=row['label']
        if set(outcomes)!=expected:raise ValueError('Every disagreement requires an explicit adjudication')
        adjudicated=dict(disagreements=len(expected),submission_sha256=digest_file(Path(adjudication)))
    result=dict(status='completed_human_structural_review' if human else 'completed_automated_supplementary_assessment',
        reviewer_type=a['reviewer_type'],reviewer_ids=[a['reviewer_id'],b['reviewer_id']],cases=n,
        labels=LABELS,confusion=matrix.tolist(),raw_agreement=observed,cohen_kappa=kappa,
        kappa_note='undefined: both marginal distributions are degenerate' if kappa is None else 'unweighted nominal-class agreement',
        human_review='two_submissions_received; adjudication_pending' if human else 'pending',
        source_manifest_sha256=manifest['source_manifest_sha256'],
        payload_sha256=manifest['payload_sha256'],
        independent_human_validation=False,adjudication=adjudicated or 'not_submitted',
        sampling='stratified diagnostic; no prevalence inference',
        limitations='Automated raters may share model priors; agreement is not correctness or social ground truth',
        submission_hashes=[digest_file(Path(first)),digest_file(Path(second))],discrepancies=discrepancies,
        generated_utc=datetime.now(timezone.utc).isoformat())
    output.mkdir(parents=True)
    for name,path in (('first.json',first),('second.json',second)):
        (output/name).write_bytes(Path(path).read_bytes())
    if adjudication is not None:(output/'adjudication.json').write_bytes(Path(adjudication).read_bytes())
    json_write(output/'summary.json',result)
    seal(output,dict(status='complete',stage='structural-assessment'))
    return result
