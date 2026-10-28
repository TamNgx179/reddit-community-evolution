"""Run a bounded retrospective component study in a new immutable directory.

The original freeze, models, labels and graphs remain untouched. No variant
selection is made from the returned scores and no human judgments are generated.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from threadpoolctl import threadpool_limits

from reddit_sna.artifacts import capture_run_provenance
from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.components import FULL, SETTINGS, definitions, load_protocol, summarize, validate_samples
from reddit_sna.evaluation.label_validation import coverage_audit
from reddit_sna.evaluation.research import KEY
from reddit_sna.evaluation.temporal_protocol import PRIMARY, months
from reddit_sna.models.activity_forecast import fit_activity_model, predict_activity_model
from reddit_sna.pipelines.study_preparation import seal, verified
from reddit_sna.pipelines.study_resources import json_write, monitored
from reddit_sna.pipelines.study_samples import read_csv, write_csv
from reddit_sna.pipelines.temporal_study import _complete


def load_cohort(root, protocol):
    """Verify archived source bindings without requiring old code to be current.

    Only immutable numeric tables and JSON are read. No archived pickle is loaded.
    Original source hashes describe their historical run rather than being reset.
    """
    root = Path(root).resolve()
    freeze_path = root/'freeze.json'
    freeze = json.loads(freeze_path.read_text(encoding='utf-8'))
    selection = (root/freeze['selection']).resolve()
    if not selection.is_relative_to(root):
        raise ValueError('Unsafe selection reference')
    verified(selection)
    if (digest_file(selection/'complete.json') != freeze['selection_manifest_sha256'] or
        digest_file(root/'protocol.json') != freeze['protocol_sha256']):
        raise ValueError('Frozen source binding mismatch')
    sources = {stage:_complete(root, stage) for stage in ('development-samples','evaluation-samples','evaluation')}
    if any(p is None for p in sources.values()):
        raise ValueError('Complete historical sample and prediction stages required')
    development = sources['development-samples']
    for relative in ('label_audit.json','review/reviewer/cases.json','review/reviewer/annotations.csv'):
        if not (development/relative).is_file():
            raise ValueError('Source audit or blinded reviewer payload is missing')
    if (development.resolve() != (root/freeze['development_samples']).resolve() or
        digest_file(development/'complete.json') != freeze['development_manifest_sha256'] or
        digest_file(development/'samples.csv') != freeze['development_samples_sha256']):
        raise ValueError('Development source differs from freeze')
    evidence = verified(sources['evaluation'])
    if (evidence['selection_manifest_sha256'] != digest_file(selection/'complete.json') or
        evidence['sample_manifest_sha256'] != digest_file(sources['evaluation-samples']/'complete.json')):
        raise ValueError('Final predictions refer to other samples or selection')
    selected = json.loads((selection/'selection.json').read_text(encoding='utf-8'))
    primary = selected['definitions'][PRIMARY]
    if (primary['settings'] != SETTINGS or primary['fields'] != definitions()[FULL]['fields'] or
        primary['hierarchical'] is not True):
        raise ValueError('Source primary differs from the matched protocol')
    dev = read_csv(development/'samples.csv')
    all_rows = read_csv(sources['evaluation-samples']/'samples.csv')
    validate_samples(dev)
    validate_samples(all_rows)
    if (any(r['label_month'] >= protocol['test_start'] for r in dev) or
        dev != [r for r in all_rows if r['label_month'] < protocol['test_start']]):
        raise ValueError('Development prefix changed or contains final labels')
    if any(r['label_month'] >= protocol['end'] for r in all_rows):
        raise ValueError('Samples extend beyond the declared evaluation')
    bindings = {str(p):digest_file(p) for p in (freeze_path, root/'protocol.json',
        selection/'complete.json', *(p/'complete.json' for p in sources.values()))}
    return dict(root=root, development=dev, samples=all_rows, stages=sources,
        archived_predictions=read_csv(sources['evaluation']/'predictions.csv'), bindings=bindings)


def evaluate_cohort(cohort, protocol, output):
    """Fit expanding origins and a fixed pre-2018 refit, saving every prediction."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    variants = definitions()
    development, samples = cohort['development'], cohort['samples']
    origins = months(protocol['validation_start'], protocol['test_start'])
    phases = [('development', month, [r for r in development if r['label_month'] < month],
               [r for r in development if r['label_month'] == month]) for month in origins]
    phases.append(('final', protocol['test_start'], development,
                   [r for r in samples if r['label_month'] >= protocol['test_start']]))
    predictions, fits = [], []
    with threadpool_limits(limits=1):
        for phase, origin, train, test in phases:
            if not train or not test or max(r['label_month'] for r in train) >= origin:
                raise ValueError('Every origin needs strictly past training and observed targets')
            for name, definition in variants.items():
                print(f'components: {output.name} {phase} {origin} {name}', flush=True)
                for seed in protocol['seeds']:
                    fitted = fit_activity_model(train, definition['fields'], definition['settings'],
                                                definition['hierarchical'], seed)
                    guesses, probabilities, flags = predict_activity_model(fitted, test)
                    fits.append(dict(phase=phase, origin=origin, model=name, seed=seed,
                        train_n=len(train), test_n=len(test), latest_train_label=fitted['latest_train_label'],
                        fallback=fitted['fallback'], support=fitted['support']))
                    for row, guess, probability, flag in zip(test, guesses, probabilities, flags):
                        record = {k:row[k] for k in (*KEY,'size')}
                        record.update(phase=phase, origin=origin, model=name, seed=seed,
                            y_true=row['label'], y_pred=guess, fallback=flag,
                            probabilities=json.dumps(probability))
                        predictions.append(record)
            # Preserve partial work if a later origin or reproduction check fails.
            write_csv(output/f'{phase}-{origin}.csv',
                      [r for r in predictions if r['phase']==phase and r['origin']==origin])
    write_csv(output/'predictions.csv', predictions)
    json_write(output/'fits.json', fits)
    # Reproduction is a mandatory gate before interpreting new component scores.
    archived = cohort['archived_predictions']
    checks = {}
    for name, old_name in ((FULL,PRIMARY),('A1_no_D','A_no_dynamics_matched')):
        old = {(int(r['seed']), *(r[k] for k in KEY)):r for r in archived if r['model']==old_name}
        new = {(int(r['seed']), *(r[k] for k in KEY)):r for r in predictions if r['phase']=='final' and r['model']==name}
        if set(old) != set(new) or not old:
            raise ValueError('Historical reproduction keys differ')
        mismatches = sum((old[k]['y_true'],old[k]['y_pred']) != (new[k]['y_true'],new[k]['y_pred']) for k in old)
        checks[name] = dict(predictions=len(old), mismatches=mismatches)
        if mismatches:
            json_write(output/'reproduction.json', checks)
            raise ValueError('Historical primary/A1 predictions not reproduced, interpretation refused')
    json_write(output/'reproduction.json', checks)
    result = {phase:summarize([r for r in predictions if r['phase']==phase], protocol['seeds'],
        list(variants), origins if phase=='development' else months(protocol['test_start'],protocol['end']),
        protocol['bootstrap_draws'], protocol['block_length'], protocol['bootstrap_seed'])
        for phase in ('development','final')}
    source = cohort['stages']['development-samples']
    audit = json.loads((source/'label_audit.json').read_text(encoding='utf-8'))
    if audit.get('status') != 'automated_rule_consistency_verified':
        raise ValueError('Saved source rule audit is not verified')
    review = source/'review/reviewer'
    readiness = dict(human_review='pending', assessment_source='automated_source_integrity_and_coverage',
        source_rule_audit=audit, coverage=coverage_audit(read_csv(source/'labels.csv'),read_csv(source/'inclusion_pairs.csv')),
        source_rule_audit_sha256=digest_file(source/'label_audit.json'),
        review_cases=str(review/'cases.json'), review_cases_sha256=digest_file(review/'cases.json'),
        actual_human_submissions=0, human_agreement=None)
    # These remain blank forms. A completed panel requires actual submissions
    # through study-agreement with truthful, independent assessor provenance.
    forms = read_csv(review/'annotations.csv')
    if any(r.get('human_label') or r.get('label') or r.get('rationale') for r in forms):
        raise ValueError('Original prepared forms are no longer blank')
    write_csv(output/'review_forms.csv', forms)
    json_write(output/'review_readiness.json', readiness)
    json_write(output/'summary.json', result)
    for path, digest in cohort['bindings'].items():
        if digest_file(Path(path)) != digest:
            raise ValueError('Source changed during controlled study')
    seal(output, dict(status='complete', stage='component-cohort', source_bindings=cohort['bindings']))
    return result


def work(protocol_path, original, external, output):
    """Internal worker. Declare the finite inventory before any controlled fits."""
    protocol = load_protocol(protocol_path)
    output = Path(output)
    sources = {name:load_cohort(root,protocol) for name,root in (('original',original),('external',external))}
    json_write(output/'declaration.json', dict(protocol=protocol, definitions=definitions(),
        declared_utc=datetime.now(timezone.utc).isoformat(),
        sources={name:c['bindings'] for name,c in sources.items()}, primary_selection='unchanged'))
    _, environment, blobs = capture_run_provenance()
    json_write(output/'environment.json', environment)
    package = Path(__file__).parents[1]
    for relative in ('evaluation/components.py','pipelines/components.py','reporting/components.py'):
        blobs[relative] = (package/relative).read_bytes()
    for name, content in blobs.items():
        path = output/'source'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    results = {name:evaluate_cohort(cohort,protocol,output/name) for name,cohort in sources.items()}
    json_write(output/'summary.json', results)
    json_write(output/'new_data_eligibility.json', dict(status='prospective_evaluation_pending',
        existing_sources={name:dict(root=str(c['root']), exposed=True) for name,c in sources.items()},
        new_untouched_cohort_verified=False, new_cohort_evaluated=False,
        requirements=['Verify source availability and prior exposure before acquisition',
            'Select corpus and periods without using final outcome distributions',
            'Freeze acquisition, graph, label, feature, model and evaluation protocol',
            'Report all six event supports and unresolved coverage without outcome-based exclusions'],
        human_review='pending', primary_replaced=False))


def run(protocol_path, original, external, output, artifact_root=Path('artifacts')):
    """Monitor one fresh output and refuse overlapping or existing destinations."""
    protocol = load_protocol(protocol_path)
    output, artifact_root = Path(output).resolve(), Path(artifact_root).resolve()
    if output == artifact_root or not output.is_relative_to(artifact_root):
        raise ValueError('Component output must be a child of artifact root')
    for source in (Path(original).resolve(),Path(external).resolve()):
        if output == source or output.is_relative_to(source) or source.is_relative_to(output):
            raise ValueError('Component output overlaps a source')
    output.mkdir(parents=True, exist_ok=False)
    command = [sys.executable,'-X','utf8','-m','reddit_sna.pipelines.components','--worker',
        '--protocol',str(Path(protocol_path).resolve()),'--original',str(Path(original).resolve()),
        '--external',str(Path(external).resolve()),'--output',str(output)]
    monitored(command,output,'controlled-components',protocol)
    seal(output,dict(status='complete',stage='controlled-components',protocol_sha256=digest_file(protocol_path)))
    return str(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', action='store_true', required=True)
    for name in ('protocol','original','external','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    work(args.protocol,args.original,args.external,args.output)
