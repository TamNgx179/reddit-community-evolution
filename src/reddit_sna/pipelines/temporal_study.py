"""Resource-bounded full-study orchestration with a frozen final-evaluation gate.

Run stages separately to inspect progress or resume complete monthly work. A
failed attempt is retained; a new attempt never overwrites its partial output.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import joblib
from threadpoolctl import threadpool_limits

from reddit_sna.artifacts import capture_run_provenance
from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.temporal_protocol import FIELDS, PRIMARY, load_temporal_protocol, months, resolved_protocol
from reddit_sna.evaluation.research import score
from reddit_sna.models.activity_forecast import fit_activity_model, predict_activity_model, select_activity_model
from reddit_sna.models.research import fit_variant, predict_variant
from reddit_sna.pipelines.study_preparation import normalize_phase, prepare_month, seal, verified
from reddit_sna.pipelines.study_resources import json_write, monitored
from reddit_sna.pipelines.study_samples import build_study_samples, read_csv, write_csv

STAGES = ('normalize-development','develop','select','evaluate','report')
LEGACY = ('B1_majority','B1_persistence')


def _complete(root, key):
    parent = Path(root) / 'stages' / key
    for path in sorted(parent.glob('attempt-*'), reverse=True):
        if (path / 'complete.json').is_file():
            verified(path)
            return path
    return None


def _attempt(root, key):
    parent = Path(root) / 'stages' / key
    parent.mkdir(parents=True, exist_ok=True)
    return parent / f'attempt-{len(list(parent.glob("attempt-*")))+1:03d}'


def _critical_sources():
    package = Path(__file__).parents[1]
    names = ('contracts.py','data/study.py','data/study_extension.py','data/normalize.py','data/archive.py','graphs/snapshots.py',
             'graphs/provenance.py','graphs/audit.py','detection/leiden.py','tracking/ged.py',
             'features/activity.py','features/community.py','features/context.py','features/history.py',
             'features/lagged.py','models/activity_forecast.py','models/research.py',
             'evaluation/temporal_protocol.py','evaluation/research_protocol.py','evaluation/research.py',
             'evaluation/study_labels.py','evaluation/study_measurement.py','evaluation/activity_forecast.py',
             'pipelines/study_preparation.py','pipelines/study_resources.py',
             'pipelines/study_samples.py','pipelines/temporal_study.py')
    return {name:digest_file(package / name) for name in names}


def _store(root, phase):
    # The implementation-stage development build is a verified source, not a
    # permission to trust an arbitrary legacy SQLite file or its sidecar name.
    initial = root / 'development-store'
    if phase=='development' and (initial/'complete.json').is_file():
        info = verified(initial)
        if info['end'] != '2018-01' or info['identity_scope'] != 'study-author-sha256-v1':
            raise ValueError('Initial development store has incompatible semantics')
        return initial
    return _complete(root, f'{phase}-store')


def _month_paths(root, end):
    result={}
    for month in months('2015-01',end):
        path=_complete(root, f'month-{month}')
        if path is None:
            raise ValueError(f'Month preparation incomplete: {month}')
        result[month]=path
    return result


def _reference(root):
    return 'activity-interaction-v1:' + hashlib.sha256((root.name+':reply-r-v3-order1:leiden-rb-gamma1-seed0').encode()).hexdigest()


def _normalize(root, raw, phase, end):
    store=_store(root,phase)
    if store is None:
        store=_attempt(root,f'{phase}-store')
        normalize_phase(raw,store,end,source=_store(root,'development') if phase=='evaluation' else None)
    return store


def _prepare(root, database, start, end):
    for month in months(start,end):
        if _complete(root,f'month-{month}') is None:
            print(f'study graph/detection: {month}',flush=True)
            prepare_month(database,_attempt(root,f'month-{month}'),month)


def _definitions():
    """Four tuned families cover fair flat, static, nonlinear dynamic and primary roles."""
    yield 'flat_lr_dynamic','dynamic','lr',False
    yield 'hier_hgb_static','static','hgb',True
    yield 'hier_hgb_dynamic','dynamic','hgb',True
    yield PRIMARY,'dynamic','lr',True


def _selection(root, protocol):
    if (root/'freeze.json').exists():
        _freeze(root)
        return
    source=_complete(root,'development-samples')
    if source is None:
        raise ValueError('Develop the full pre-2018 cohort before selection')
    if _complete(root,'measurement') is None:
        raise ValueError('Complete development measurement sensitivity before selection')
    rows=read_csv(source/'samples.csv')
    if any(r['label_month']>=protocol['test_start'] for r in rows):
        raise ValueError('Test labels must not enter selection')
    output=_attempt(root,'selection')
    output.mkdir()
    selected, evidence, definitions = {}, [], {}
    origins=months(protocol['validation_start'],protocol['test_start'])
    with threadpool_limits(limits=1):
        for name,family,estimator,hierarchical in _definitions():
            print(f'study selection: {name}',flush=True)
            result,predictions=select_activity_model(rows,FIELDS[family],estimator,hierarchical,origins)
            selected[name]=result
            evidence.extend(dict(model=name,**r) for r in predictions)
            definitions[name]=dict(kind='activity',fields=list(FIELDS[family]),settings=result['settings'],
                                   hierarchical=hierarchical)
        baseline_names=[name for name in selected if name!=PRIMARY]
        proposed=PRIMARY
        champion=max(baseline_names,key=lambda n:selected[n]['macro_f1'])
        chosen=definitions[proposed]
        for name,fields,hier in (('A_no_dynamics_matched',FIELDS['static'],True),):
            definitions[name]=dict(kind='activity',fields=list(fields),settings=chosen['settings'],hierarchical=hier)
        for name in LEGACY:
            definitions[name]=dict(kind='legacy')
            baseline_names.append(name)
            # Legacy variants have one fixed configuration, not an eight-setting
            # search. They still compete for the validation-selected champion.
            predictions=[]
            for month in origins:
                train=[r for r in rows if r['label_month']<month]
                valid=[r for r in rows if r['label_month']==month]
                fitted=fit_variant(name,train,42)
                guesses,flags=predict_variant(fitted,valid)
                predictions.extend(dict(y_true=r['label'],y_pred=p,fallback=f) for r,p,f in zip(valid,guesses,flags))
            selected[name]=dict(macro_f1=score(predictions)['macro_f1_six'],settings='legacy_fixed')
        champion=max(baseline_names,key=lambda n:selected[n]['macro_f1'])
        for name,definition in definitions.items():
            for seed in protocol['seeds']:
                fitted=(fit_variant(name,rows,seed) if definition['kind']=='legacy' else
                    fit_activity_model(rows,definition['fields'],definition['settings'],definition['hierarchical'],seed))
                joblib.dump(fitted,output/f'{name}-{seed}.joblib')
    json_write(output/'selection.json',dict(selected=selected,definitions=definitions,proposed=proposed,
        champion=champion,baselines=baseline_names,models=list(definitions),
        final_training_n=len(rows),latest_training_label=max(r['label_month'] for r in rows)))
    write_csv(output/'validation_predictions.csv',evidence)
    _,environment,blobs=capture_run_provenance()
    for name,blob in blobs.items():
        path=output/'source'/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(blob)
    json_write(output/'environment.json',environment)
    seal(output,dict(status='complete',stage='selection',development_samples_sha256=digest_file(source/'samples.csv')))
    # This is the one-way scientific gate. Later test outcomes cannot replace
    # selected settings or choose a different primary proposed method.
    json_write(root/'freeze.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
        selection=str(output.relative_to(root)),selection_manifest_sha256=digest_file(output/'complete.json'),
        development_samples=str(source.relative_to(root)),development_samples_sha256=digest_file(source/'samples.csv'),
        development_manifest_sha256=digest_file(source/'complete.json'),
        critical_source_hashes=_critical_sources(),protocol_sha256=digest_file(root/'protocol.json'),
        exposure=dict(known='2015 forecasts and full-period aggregate inventory inspected',
                      previous_post2015_forecast_exposure='not independently established',unseen=False)))


def _freeze(root):
    freeze=json.loads((root/'freeze.json').read_text(encoding='utf-8'))
    selection=(root/freeze['selection']).resolve()
    if not selection.is_relative_to(root) or digest_file(selection/'complete.json')!=freeze['selection_manifest_sha256']:
        raise ValueError('Frozen selection reference mismatch')
    verified(selection)
    if freeze['critical_source_hashes']!=_critical_sources() or freeze['protocol_sha256']!=digest_file(root/'protocol.json'):
        raise ValueError('Scientific code/protocol changed after freeze; do not evaluate or retune')
    source=(root/freeze['development_samples']).resolve()
    if not source.is_relative_to(root) or digest_file(source/'samples.csv')!=freeze['development_samples_sha256']:
        raise ValueError('Frozen development source changed')
    if digest_file(source/'complete.json')!=freeze['development_manifest_sha256']:
        raise ValueError('Frozen development feature/label inventory changed')
    verified(source)
    return selection,source


def _evaluate(root, raw, protocol):
    selection,development=_freeze(root)
    if _complete(root,'evaluation') is not None:
        return
    store=_normalize(root,raw,'evaluation',protocol['end'])
    _prepare(root,store/'normalized.sqlite',protocol['test_start'],protocol['end'])
    source=_complete(root,'evaluation-samples')
    if source is None:
        source=_attempt(root,'evaluation-samples')
        build_study_samples(store/'normalized.sqlite',_month_paths(root,protocol['end']),source,_reference(root),cache=development)
    rows=read_csv(source/'samples.csv')
    old=read_csv(development/'samples.csv')
    prefix=[r for r in rows if r['label_month']<protocol['test_start']]
    if old!=prefix:
        raise ValueError('Final metadata changed development features/labels; evaluation refused')
    test=[r for r in rows if r['label_month']>=protocol['test_start']]
    frozen=json.loads((selection/'selection.json').read_text(encoding='utf-8'))
    predictions=[]
    with threadpool_limits(limits=1):
        for name,definition in frozen['definitions'].items():
            for seed in protocol['seeds']:
                fitted=joblib.load(selection/f'{name}-{seed}.joblib')
                if definition['kind']=='legacy':
                    guessed,flags=predict_variant(fitted,test)
                    probabilities=[None]*len(test)
                else:
                    guessed,probabilities,flags=predict_activity_model(fitted,test)
                predictions.extend(dict(**{k:r[k] for k in ('reference_id','feature_month','community_id','label_month','label_reference_id','size')},
                    model=name,seed=seed,y_true=r['label'],y_pred=p,fallback=f,
                    probabilities=json.dumps(prob)) for r,p,prob,f in zip(test,guessed,probabilities,flags))
    from reddit_sna.evaluation.activity_forecast import evaluate_activity_predictions
    results=evaluate_activity_predictions(predictions,protocol['seeds'],frozen['models'],
        months(protocol['test_start'],protocol['end']),frozen['proposed'],frozen['champion'],frozen['baselines'],
        protocol['bootstrap_draws'],protocol['block_length'],protocol['bootstrap_seed'])
    _freeze(root)
    output=_attempt(root,'evaluation')
    output.mkdir()
    write_csv(output/'predictions.csv',predictions)
    json_write(output/'evaluation.json',results)
    seal(output,dict(status='complete',stage='evaluation',sample_manifest_sha256=digest_file(source/'complete.json'),
        selection_manifest_sha256=digest_file(selection/'complete.json'),superiority=results['superiority']))


def worker(root, raw, stage, protocol):
    """Internal subprocess stage; public entry points apply resource monitoring."""
    if stage=='normalize-development':
        _normalize(root,raw,'development',protocol['test_start'])
    elif stage=='develop':
        store=_store(root,'development')
        if store is None:
            raise ValueError('Normalize development metadata first')
        _prepare(root,store/'normalized.sqlite',protocol['start'],protocol['test_start'])
        if _complete(root,'development-samples') is None:
            build_study_samples(store/'normalized.sqlite',_month_paths(root,protocol['test_start']),
                _attempt(root,'development-samples'),_reference(root))
        if _complete(root,'measurement') is None:
            from reddit_sna.evaluation.study_measurement import measurement_diagnostics
            output=_attempt(root,'measurement')
            measurement_diagnostics(_month_paths(root,protocol['test_start']),output)
            seal(output,dict(status='complete',stage='measurement',primary_reference_changed=False))
    elif stage=='select':
        _selection(root,protocol)
    elif stage=='evaluate':
        _evaluate(root,raw,protocol)
    elif stage=='report':
        from reddit_sna.reporting.temporal_study import write_study_report
        write_study_report(root)
    else:
        raise ValueError('Unknown study stage')


def run_temporal_study(protocol_path, raw, root, stage, artifact_root=Path('artifacts')):
    """Create/resume an explicit study; no generic pipeline behavior is changed."""
    root,raw,artifact_root=map(lambda p:Path(p).resolve(),(root,raw,artifact_root))
    if not root.is_relative_to(artifact_root) or root==artifact_root or root.is_relative_to(raw) or raw.is_relative_to(root):
        raise ValueError('Study run must be a separate child of artifacts')
    if stage not in STAGES:
        raise ValueError('Unknown study stage')
    protocol=load_temporal_protocol(protocol_path)
    root.mkdir(parents=True,exist_ok=True)
    resolved=resolved_protocol(protocol)
    path=root/'protocol.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8'))!=json.loads(json.dumps(resolved)):
            raise ValueError('Existing study protocol differs')
    else:
        json_write(path,resolved)
    if stage in ('evaluate','report'):
        _freeze(root)
    attempts=len(list((root/'resources').glob(stage+'-*.json')))
    command=[sys.executable,'-X','utf8','-m','reddit_sna.pipelines.temporal_study','--worker',
             '--root',str(root),'--raw',str(raw),'--stage',stage,'--protocol',str(Path(protocol_path).resolve())]
    return monitored(command,root,f'{stage}-{attempts+1:03d}',protocol)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',action='store_true',required=True)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--raw',type=Path,required=True)
    parser.add_argument('--stage',choices=STAGES,required=True)
    parser.add_argument('--protocol',type=Path,required=True)
    args=parser.parse_args()
    worker(args.root.resolve(),args.raw.resolve(),args.stage,load_temporal_protocol(args.protocol))
