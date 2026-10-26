"""Bind supplementary technical judgments to actual structural case evidence.

This tool never certifies a human reviewer. Completion means a source-bound
technical assessment exists, not that social validity or human agreement holds.
"""

from collections import Counter
from datetime import datetime
import json
from pathlib import Path

from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.temporal_protocol import EVENTS
from reddit_sna.pipelines.study_preparation import seal, verified
from reddit_sna.pipelines.study_resources import json_write
from reddit_sna.pipelines.study_samples import write_csv

LABELS = (*EVENTS,'unresolved')


def complete_assessment(panel, submission, output):
    """Validate all source-bound judgments before opening the coordinator key."""
    panel,submission,output = Path(panel).resolve(),Path(submission).resolve(),Path(output).resolve()
    if output.exists():raise FileExistsError('Preserve prior assessment results')
    if output==panel or output.is_relative_to(panel) or panel.is_relative_to(output):
        raise ValueError('Assessment output must not modify the original panel')
    verified(panel)
    metadata = json.loads((panel/'manifest.json').read_text(encoding='utf-8'))
    payload = panel/'reviewer/cases.json'
    if digest_file(payload) != metadata['payload_sha256']:
        raise ValueError('Assessment payload differs from the sealed panel')
    cases = json.loads(payload.read_text(encoding='utf-8'))
    indexed = {r['case_id']:r for r in cases}
    if not indexed or len(indexed)!=len(cases):raise ValueError('Empty or duplicated structural cases')
    supplied = json.loads(submission.read_text(encoding='utf-8'))
    if (supplied.get('reviewer_type')!='automated' or
        not supplied.get('reviewer_id','').startswith('technical-') or
        not supplied.get('provenance','').strip() or
        supplied.get('payload_sha256')!=metadata['payload_sha256'] or
        supplied.get('machine_answers_not_seen') is not True or
        supplied.get('model_predictions_not_seen') is not True):
        raise ValueError('Technical assessment requires truthful non-human provenance and source binding')
    try:
        timestamp = datetime.fromisoformat(supplied['submitted_utc'].replace('Z','+00:00'))
        if timestamp.tzinfo is None:raise ValueError('Timezone required')
    except (KeyError,TypeError,ValueError,AttributeError) as error:
        raise ValueError('Timezone-aware actual submission timestamp required') from error
    judgments = {}
    for row in supplied.get('judgments',[]):
        key = row['case_id']
        if key not in indexed or key in judgments or row['label'] not in LABELS:
            raise ValueError('Missing, duplicated or unknown case judgment')
        case = indexed[key]
        claims = row.get('evidence',{})
        expected = dict(source_size=case['source_size'],overlapping_targets=len(case['targets']),
                        largest_shared=max((t['shared'] for t in case['targets']),default=0))
        if (claims!=expected or row.get('confidence') not in ('low','medium','high') or
            len(row.get('rationale','').strip())<25):
            raise ValueError('Each judgment needs actual numeric evidence and a substantive rationale')
        judgments[key] = row
    if set(judgments)!=set(indexed):raise ValueError('Incomplete assessments cannot mark a panel complete')
    # Machine targets are opened only after the assessment has been supplied.
    answers = json.loads((panel/'coordinator/answers.json').read_text(encoding='utf-8'))
    key = {r['case_id']:r for r in answers}
    if (len(key)!=len(answers) or set(key)!=set(indexed) or
        any((r['label'] or 'unresolved') not in LABELS for r in answers)):
        raise ValueError('Coordinator key differs from the case payload')
    comparisons = [dict(case_id=cid,machine=key[cid]['label'] or 'unresolved',
        assessed=judgments[cid]['label'],confidence=judgments[cid]['confidence'],
        matches=(key[cid]['label'] or 'unresolved')==judgments[cid]['label']) for cid in indexed]
    confusion = [[sum(r['machine']==a and r['assessed']==b for r in comparisons) for b in LABELS] for a in LABELS]
    summary = dict(cases=len(comparisons),reviewer_type='automated',reviewer_id=supplied['reviewer_id'],
        provenance=supplied['provenance'],source_manifest_sha256=metadata['source_manifest_sha256'],
        payload_sha256=metadata['payload_sha256'],submission_sha256=digest_file(submission),
        technical_machine_concordance=sum(r['matches'] for r in comparisons)/len(comparisons),
        discrepancies=sum(not r['matches'] for r in comparisons),labels=LABELS,confusion=confusion,
        assessed_support=dict(Counter(r['assessed'] for r in comparisons)),human_review='pending',
        independent_human_submissions=0,human_agreement=None,
        scope='Technical structural plausibility on a stratified panel, not social ground truth or population accuracy')
    output.mkdir(parents=True,exist_ok=False)
    (output/'submission.json').write_bytes(submission.read_bytes())
    write_csv(output/'comparisons.csv',comparisons)
    json_write(output/'summary.json',summary)
    seal(output,dict(status='complete',stage='technical-structural-assessment',
                     source_panel_manifest_sha256=digest_file(panel/'complete.json')))
    return summary
