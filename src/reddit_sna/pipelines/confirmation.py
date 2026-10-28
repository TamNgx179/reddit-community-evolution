"""Locked external-corpus replication; never retune on confirmation outcomes.

Original model settings are copied explicitly into a versioned declaration.
New-cohort models are fit through December 2017, then frozen before any 2018
reference partitions or targets are prepared. Old study artifacts stay intact.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tomllib

import joblib
from threadpoolctl import threadpool_limits

from reddit_sna.artifacts import capture_run_provenance
from reddit_sna.data.archive import digest_file
from reddit_sna.data.confirmation import CORPORA, acquire
from reddit_sna.evaluation.activity_forecast import evaluate_activity_predictions
from reddit_sna.evaluation.temporal_protocol import COMPACT_BASELINES, COMPACT_MODELS, FIELDS, PRIMARY, months
from reddit_sna.models.activity_forecast import fit_activity_model, predict_activity_model
from reddit_sna.models.research import fit_variant, predict_variant
from reddit_sna.pipelines.study_preparation import normalize_phase, prepare_month, seal, verified
from reddit_sna.pipelines.study_resources import json_write, monitored
from reddit_sna.pipelines.study_samples import build_study_samples, read_csv, write_csv
from reddit_sna.pipelines.temporal_study import _attempt, _complete

STAGES = ('acquire', 'develop', 'fit', 'evaluate')


def load_protocol(path):
    """Load one bounded, declared replication; old study schedules are unchanged."""
    path = Path(path).resolve()
    protocol = tomllib.loads(path.read_text(encoding='utf-8'))
    expected = dict(schema_version=1, protocol_id='external-political-cohort-confirmation-v1',
        corpora=list(CORPORA), start='2015-01', test_start='2018-01', end='2018-10',
        seeds=[42,43,44], bootstrap_draws=2000, block_length=3, bootstrap_seed=2026,
        working_budget_gib=30, memory_budget_gib=8, minimum_free_gib=12,
        models='configs/confirmation_models.json', review_per_stratum=5, review_seed=2026,
        context_entropy_denominator=3,
        exposure='external_corpus_replication; prior_group_exposure_uncertified; users_may_overlap')
    if json.dumps(protocol,sort_keys=True) != json.dumps(expected,sort_keys=True):
        raise ValueError('Unsupported confirmation protocol; create a separately reviewed version')
    model_path = path.parent / 'confirmation_models.json'
    models = json.loads(model_path.read_text(encoding='utf-8'))
    if (models.get('schema_version') != 1 or models.get('primary') != PRIMARY or
        models.get('champion') != 'hier_hgb_dynamic' or
        models.get('baselines') != list(COMPACT_BASELINES) or
        tuple(models.get('definitions',{})) != COMPACT_MODELS):
        raise ValueError('Confirmation must retain the seven declared method roles')
    definitions = {}
    for name, item in models['definitions'].items():
        item = dict(item)
        if item['kind'] == 'activity':
            family = item.pop('family')
            if family not in FIELDS:
                raise ValueError('Unknown declared feature family')
            item['fields'] = list(FIELDS[family])
        elif item['kind'] != 'legacy' or name not in ('B1_majority','B1_persistence'):
            raise ValueError('Unknown confirmation model')
        definitions[name] = item
    return protocol, models, definitions, model_path


def _source_hashes():
    """Freeze the complete product package, including cohort/feature adapters."""
    package = Path(__file__).parents[1]
    return {p.relative_to(package).as_posix():digest_file(p) for p in sorted(package.rglob('*.py'))}


def frozen(root):
    """Reject post-fit source, model, sample or protocol drift before evaluation."""
    root = Path(root)
    freeze = json.loads((root/'freeze.json').read_text(encoding='utf-8'))
    if freeze['critical_source_hashes'] != _source_hashes() or freeze['protocol_sha256'] != digest_file(root/'protocol.json'):
        raise ValueError('Confirmation source/protocol changed after fit')
    selection = (root/freeze['selection']).resolve()
    development = (root/freeze['development_samples']).resolve()
    if not selection.is_relative_to(root.resolve()) or not development.is_relative_to(root.resolve()):
        raise ValueError('Unsafe frozen source reference')
    verified(selection); verified(development)
    if (digest_file(selection/'complete.json') != freeze['selection_manifest_sha256'] or
        digest_file(development/'complete.json') != freeze['development_manifest_sha256']):
        raise ValueError('Frozen confirmation inputs changed')
    return selection, development


def _month_paths(root, end, protocol):
    return {month:_complete(root,f'month-{month}') for month in months(protocol['start'],end)}


def _prepare(root, store, start, end, protocol):
    for month in months(start,end):
        if _complete(root,f'month-{month}') is None:
            print(f'confirmation graph: {month}',flush=True)
            prepare_month(store/'normalized.sqlite',_attempt(root,f'month-{month}'),month,corpora=CORPORA)


def _reference(root):
    return 'external-political-v1:'+digest_file(Path(root)/'protocol.json')


def worker(root, protocol, definitions, stage):
    """Execute a single monitored phase with immutable success checkpoints."""
    if stage == 'acquire':
        acquire(root/'raw',protocol['minimum_free_gib'])
    elif stage == 'develop':
        store = _complete(root,'development-store')
        if store is None:
            store = _attempt(root,'development-store')
            normalize_phase(root/'raw',store,protocol['test_start'],corpora=CORPORA)
        _prepare(root,store,protocol['start'],protocol['test_start'],protocol)
        if _complete(root,'development-samples') is None:
            build_study_samples(store/'normalized.sqlite',_month_paths(root,protocol['test_start'],protocol),
                _attempt(root,'development-samples'),_reference(root),corpora=CORPORA)
    elif stage == 'fit':
        if (root/'freeze.json').exists():
            frozen(root)
            return
        source = _complete(root,'development-samples')
        if source is None:
            raise ValueError('Complete development before freezing models')
        rows = read_csv(source/'samples.csv')
        if not rows or any(r['label_month'] >= protocol['test_start'] for r in rows):
            raise ValueError('Final outcomes entered confirmation fitting')
        output = _attempt(root,'selection'); output.mkdir()
        with threadpool_limits(limits=1):
            for name, definition in definitions.items():
                for seed in protocol['seeds']:
                    fitted = (fit_variant(name,rows,seed) if definition['kind']=='legacy' else
                        fit_activity_model(rows,definition['fields'],definition['settings'],definition['hierarchical'],seed))
                    joblib.dump(fitted,output/f'{name}-{seed}.joblib')
        json_write(output/'selection.json',dict(definitions=definitions,models=list(COMPACT_MODELS),
            baselines=list(COMPACT_BASELINES),proposed=PRIMARY,champion='hier_hgb_dynamic',
            selected={},selection_policy='original settings fixed before new outcomes; no new tuning',
            final_training_n=len(rows),latest_training_label=max(r['label_month'] for r in rows)))
        _, environment, blobs = capture_run_provenance()
        for name,blob in blobs.items():
            target=output/'source'/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(blob)
        json_write(output/'environment.json',environment)
        seal(output,dict(status='complete',stage='selection'))
        json_write(root/'freeze.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
            selection=str(output.relative_to(root)),selection_manifest_sha256=digest_file(output/'complete.json'),
            development_samples=str(source.relative_to(root)),development_samples_sha256=digest_file(source/'samples.csv'),
            development_manifest_sha256=digest_file(source/'complete.json'),critical_source_hashes=_source_hashes(),
            protocol_sha256=digest_file(root/'protocol.json'),
            exposure=dict(kind='external-corpus replication',unseen=False,independent_users=False,
                prior_group_exposure='uncertified',new_cohort_targets_prepared_after_freeze=True)))
    elif stage == 'evaluate':
        selection,development = frozen(root)
        if _complete(root,'evaluation') is not None:
            return
        store = _complete(root,'evaluation-store')
        if store is None:
            store = _attempt(root,'evaluation-store')
            normalize_phase(root/'raw',store,protocol['end'],source=_complete(root,'development-store'),corpora=CORPORA)
        _prepare(root,store,protocol['test_start'],protocol['end'],protocol)
        source = _complete(root,'evaluation-samples')
        if source is None:
            source = _attempt(root,'evaluation-samples')
            build_study_samples(store/'normalized.sqlite',_month_paths(root,protocol['end'],protocol),
                source,_reference(root),cache=development,corpora=CORPORA)
        rows = read_csv(source/'samples.csv')
        if [r for r in rows if r['label_month']<protocol['test_start']] != read_csv(development/'samples.csv'):
            raise ValueError('New final metadata changed the development prefix')
        test = [r for r in rows if r['label_month']>=protocol['test_start']]
        predictions = []
        with threadpool_limits(limits=1):
            for name,definition in definitions.items():
                for seed in protocol['seeds']:
                    fitted = joblib.load(selection/f'{name}-{seed}.joblib')
                    if definition['kind']=='legacy':
                        guessed,flags=predict_variant(fitted,test);probabilities=[None]*len(test)
                    else:
                        guessed,probabilities,flags=predict_activity_model(fitted,test)
                    predictions.extend(dict(**{k:r[k] for k in ('reference_id','feature_month','community_id','label_month','label_reference_id','size')},
                        model=name,seed=seed,y_true=r['label'],y_pred=p,fallback=f,probabilities=json.dumps(prob))
                        for r,p,prob,f in zip(test,guessed,probabilities,flags))
        results=evaluate_activity_predictions(predictions,protocol['seeds'],COMPACT_MODELS,
            months(protocol['test_start'],protocol['end']),PRIMARY,'hier_hgb_dynamic',COMPACT_BASELINES,
            protocol['bootstrap_draws'],protocol['block_length'],protocol['bootstrap_seed'])
        frozen(root)
        output=_attempt(root,'evaluation');output.mkdir()
        write_csv(output/'predictions.csv',predictions);json_write(output/'evaluation.json',results)
        seal(output,dict(status='complete',stage='evaluation',
            sample_manifest_sha256=digest_file(source/'complete.json'),selection_manifest_sha256=digest_file(selection/'complete.json')))
    else:
        raise ValueError('Unknown confirmation stage')


def run_confirmation(protocol_path, root, stage, artifact_root=Path('artifacts')):
    """Run a new external replication, never an overwrite of the original study."""
    root=Path(root).resolve();artifact_root=Path(artifact_root).resolve()
    if not root.is_relative_to(artifact_root) or root==artifact_root or stage not in STAGES:
        raise ValueError('Confirmation needs an explicit child of artifacts and a known stage')
    protocol,models,definitions,model_path=load_protocol(protocol_path)
    root.mkdir(parents=True,exist_ok=True)
    declaration=root/'declaration.json'
    if declaration.exists():
        saved=json.loads(declaration.read_text(encoding='utf-8'))
        if saved['protocol']!=protocol or saved['models']!=models:
            raise ValueError('Pre-acquisition confirmation declaration changed')
    else:
        json_write(declaration,dict(protocol=protocol,models=models,
            declared_utc=datetime.now(timezone.utc).isoformat(),confirmation_outcomes_read=False))
    resolved=dict(protocol,fields={name:list(fields) for name,fields in FIELDS.items()},
        model_declaration_sha256=digest_file(model_path),context_entropy_normalization='log(3); old log(15) default preserved')
    path=root/'protocol.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=resolved:
        raise ValueError('Stored confirmation protocol changed')
    if not path.exists():json_write(path,resolved)
    if stage=='evaluate':frozen(root)
    count=len(list((root/'resources').glob(stage+'-*.json')))
    command=[sys.executable,'-X','utf8','-m',__name__,'--worker','--root',str(root),
             '--protocol',str(Path(protocol_path).resolve()),'--stage',stage]
    return monitored(command,root,f'{stage}-{count+1:03d}',protocol)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',action='store_true',required=True)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--stage',choices=STAGES,required=True)
    args=parser.parse_args()
    protocol,_,definitions,_=load_protocol(args.protocol)
    worker(args.root.resolve(),protocol,definitions,args.stage)
