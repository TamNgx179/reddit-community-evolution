"""Pre-acquisition declared replication of a fixed history-pruned candidate.

Declare, acquire, develop, fit and evaluate are separate monitored stages. Final
graphs and targets cannot be prepared until all models and source hashes freeze.
Historical runs and their fixed-cohort adapters are never rewritten.
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
from reddit_sna.data.prospective import acquire, normalize, validate_archive
from reddit_sna.evaluation.activity_forecast import evaluate_activity_predictions
from reddit_sna.evaluation.components import summarize
from reddit_sna.evaluation.temporal_protocol import COMPACT_BASELINES, COMPACT_MODELS, FIELDS, PRIMARY, months
from reddit_sna.models.activity_forecast import fit_activity_model, predict_activity_model
from reddit_sna.models.research import fit_variant, predict_variant
from reddit_sna.pipelines.confirmation import _source_hashes
from reddit_sna.pipelines.study_preparation import prepare_month, seal, verified
from reddit_sna.pipelines.study_resources import json_write, monitored
from reddit_sna.pipelines.study_samples import build_study_samples, read_csv, write_csv
from reddit_sna.pipelines.temporal_study import _attempt, _complete

CORPORA = ('Anarchism','Libertarian','GreenParty')
CANDIDATE = 'hier_lr_pruned_growth'
FLAT_CONTROL = 'A_flat_pruned_matched'
REMOVED = ('record_log_growth','reply_log_growth')
STAGES = ('acquire','develop','fit','evaluate','review')


def panel_path(root):
    """Keep review copies outside the immutable scientific study directory."""
    root = Path(root)
    return root.parent/(root.name+'-structural-panel')


def model_definitions(model_path):
    """Transfer original baseline settings and predeclare the 35-field candidate."""
    document = json.loads(Path(model_path).read_text(encoding='utf-8'))
    if (tuple(document['definitions']) != COMPACT_MODELS or
        document['primary'] != PRIMARY or document['baselines'] != list(COMPACT_BASELINES)):
        raise ValueError('Historical baseline declaration differs')
    definitions = {}
    for name,raw in document['definitions'].items():
        item = dict(raw)
        if item['kind']=='activity':
            family = item.pop('family')
            item['fields'] = list(FIELDS[family])
        definitions[name] = item
    primary = definitions[PRIMARY]
    if primary['settings'] != dict(estimator='lr',C=1.,class_weight='balanced',transform='standard'):
        raise ValueError('Primary settings differ from controlled comparison')
    fields = [f for f in primary['fields'] if f not in REMOVED]
    if len(fields)!=35:
        raise ValueError('Pruned candidate must remove exactly two growth fields')
    definitions[CANDIDATE] = dict(kind='activity',fields=fields,settings=dict(primary['settings']),hierarchical=True)
    definitions[FLAT_CONTROL] = dict(kind='activity',fields=list(fields),settings=dict(primary['settings']),hierarchical=False)
    return definitions


def load_protocol(path):
    """Admit one reviewed cohort and schedule, never outcome-driven alternatives."""
    path = Path(path).resolve()
    protocol = tomllib.loads(path.read_text(encoding='utf-8'))
    expected = dict(schema_version=1,protocol_id='prospective-ideological-cohort-v1',corpora=list(CORPORA),
        start='2015-01',test_start='2018-01',end='2018-10',seeds=[42,43,44],bootstrap_draws=2000,
        block_length=3,bootstrap_seed=2026,working_budget_gib=30,memory_budget_gib=8,minimum_free_gib=12,
        models='confirmation_models.json',primary=CANDIDATE,champion='hier_hgb_dynamic',
        review_seed=20261026,review_per_stratum=3,
        exposure='new_to_this_run_after_declaration_team_exposure_uncertified_users_may_overlap')
    archives = protocol.get('archives',{})
    if {k:v for k,v in protocol.items() if k!='archives'} != expected or set(archives)!=set(CORPORA):
        raise ValueError('Unsupported prospective protocol')
    sizes = dict(Anarchism=228362409,Libertarian=920449141,GreenParty=4398276)
    directories = dict(Anarchism='AmericanPorn~-~Androgynoushotties',Libertarian='LiberalAdvance~-~LifeProTips',
                       GreenParty='GrandTheftAutoV4x4~-~Guelph')
    for name,item in archives.items():
        validate_archive(name,item)
        url = 'https://zissou.infosci.cornell.edu/convokit/datasets/subreddit-corpus/corpus-zipped/'+directories[name]+'/'+name+'.corpus.zip'
        if item != dict(url=url,bytes=sizes[name]):
            raise ValueError('Archive differs from the checked pre-acquisition catalogue')
    model_path = path.parent/protocol['models']
    return protocol,model_definitions(model_path),model_path


def declare(root, protocol, definitions, protocol_path, model_path):
    """Write once before acquisition and reject any later declaration drift."""
    root = Path(root)
    resolved = dict(protocol,definitions=definitions,model_declaration_sha256=digest_file(model_path),
        context_entropy_denominator=len(CORPORA),graph='reply-r-v3-order1 weighted Leiden RB gamma1 seed0',
        labels='GED-adapted alpha=.5 beta=.5 dissolve=.1, unresolved excluded, final snapshot censored')
    path = root/'protocol.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != resolved:
            raise ValueError('Prospective pre-acquisition declaration changed')
        saved = json.loads((root/'declaration.json').read_text(encoding='utf-8'))
        if (saved['protocol_sha256'] != digest_file(path) or saved['definitions'] != definitions or
            saved['config_sha256'] != digest_file(protocol_path)):
            raise ValueError('Prospective acquisition declaration binding changed')
        return
    if any(root.iterdir()):
        raise ValueError('A new prospective declaration requires an empty destination')
    json_write(path,resolved)
    json_write(root/'declaration.json',dict(declared_utc=datetime.now(timezone.utc).isoformat(),
        protocol_sha256=digest_file(path),config_sha256=digest_file(protocol_path),
        candidate_outcome_records_read=False,raw_archives_present=False,definitions=definitions,
        primary_fixed=CANDIDATE,baseline_roles=list(COMPACT_BASELINES),
        prior_team_exposure='uncertified',independent_users=False))


def frozen(root):
    """Verify source, immutable model inventory and development reference bindings."""
    root = Path(root).resolve()
    record = json.loads((root/'freeze.json').read_text(encoding='utf-8'))
    if (record['source_hashes'] != _source_hashes() or record['protocol_sha256'] != digest_file(root/'protocol.json') or
        record['declaration_sha256'] != digest_file(root/'declaration.json')):
        raise ValueError('Prospective scientific source or protocol changed after fitting')
    paths = [(root/record[k]).resolve() for k in ('selection','development_samples')]
    if any(not p.is_relative_to(root) for p in paths):
        raise ValueError('Unsafe frozen model/sample path')
    for path,key in zip(paths,('selection_manifest_sha256','development_manifest_sha256')):
        verified(path)
        if digest_file(path/'complete.json') != record[key]:
            raise ValueError('Prospective fitted inputs changed')
    return tuple(paths)


def _paths(root, protocol, end):
    paths = {m:_complete(root,'month-'+m) for m in months(protocol['start'],end)}
    if any(p is None for p in paths.values()):
        raise ValueError('Missing declared prospective snapshot')
    return paths


def _prepare(root, store, protocol, start, end):
    for month in months(start,end):
        if _complete(root,'month-'+month) is None:
            print('prospective graph: '+month,flush=True)
            prepare_month(store/'normalized.sqlite',_attempt(root,'month-'+month),month,corpora=CORPORA)


def work(root, protocol, definitions, stage):
    """Execute one stage. No evaluation method can alter a chosen configuration."""
    root = Path(root)
    declared = json.loads((root/'protocol.json').read_text(encoding='utf-8'))
    if declared['definitions'] != definitions or any(declared.get(k)!=v for k,v in protocol.items()):
        raise ValueError('Worker configuration differs from pre-acquisition declaration')
    reference = 'prospective-ideological-v1:'+digest_file(root/'protocol.json')
    if stage=='acquire':
        acquired = acquire(root/'raw',protocol['archives'],protocol['minimum_free_gib'])
        if not (root/'acquisition.json').exists():
            json_write(root/'acquisition.json',dict(archives=acquired,completed_utc=datetime.now(timezone.utc).isoformat(),
                declaration_sha256=digest_file(root/'declaration.json')))
    elif stage=='develop':
        if not (root/'acquisition.json').is_file():raise ValueError('Acquire the fixed cohort first')
        store = _complete(root,'development-store')
        if store is None:
            store = _attempt(root,'development-store')
            normalize(root/'raw',store,protocol['test_start'],protocol['archives'])
        _prepare(root,store,protocol,protocol['start'],protocol['test_start'])
        if _complete(root,'development-samples') is None:
            build_study_samples(store/'normalized.sqlite',_paths(root,protocol,protocol['test_start']),
                _attempt(root,'development-samples'),reference,corpora=CORPORA)
    elif stage=='fit':
        if (root/'freeze.json').exists():
            frozen(root)
            return
        source = _complete(root,'development-samples')
        if source is None:raise ValueError('Complete development before model freeze')
        rows = read_csv(source/'samples.csv')
        if not rows or any(r['label_month']>=protocol['test_start'] for r in rows):
            raise ValueError('Final labels entered prospective fitting')
        output = _attempt(root,'selection')
        output.mkdir()
        with threadpool_limits(limits=1):
            for name,item in definitions.items():
                print('prospective fit: '+name,flush=True)
                for seed in protocol['seeds']:
                    fitted = fit_variant(name,rows,seed) if item['kind']=='legacy' else fit_activity_model(
                        rows,item['fields'],item['settings'],item['hierarchical'],seed)
                    joblib.dump(fitted,output/f'{name}-{seed}.joblib')
        json_write(output/'selection.json',dict(definitions=definitions,models=list(definitions),
            baselines=list(COMPACT_BASELINES),proposed=CANDIDATE,champion=protocol['champion'],selected={},
            selection_policy='all settings fixed before new acquisition, no new tuning',
            final_training_n=len(rows),latest_training_label=max(r['label_month'] for r in rows)))
        _,environment,blobs = capture_run_provenance()
        json_write(output/'environment.json',environment)
        for name,blob in blobs.items():
            path=output/'source'/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(blob)
        seal(output,dict(status='complete',stage='selection'))
        json_write(root/'freeze.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
            selection=str(output.relative_to(root)),selection_manifest_sha256=digest_file(output/'complete.json'),
            development_samples=str(source.relative_to(root)),development_manifest_sha256=digest_file(source/'complete.json'),
            development_samples_sha256=digest_file(source/'samples.csv'),
            source_hashes=_source_hashes(),protocol_sha256=digest_file(root/'protocol.json'),
            declaration_sha256=digest_file(root/'declaration.json'),final_targets_prepared=False,
            new_to_this_run=True,independent_users=False,prior_team_exposure='uncertified',
            exposure=dict(new_to_this_run=True,unseen=False,prior_team_exposure='uncertified',
                          independent_users=False,final_targets_prepared_after_model_freeze=True)))
    elif stage=='evaluate':
        selection,development = frozen(root)
        if _complete(root,'evaluation') is not None:return
        store = _complete(root,'evaluation-store')
        if store is None:
            store = _attempt(root,'evaluation-store')
            normalize(root/'raw',store,protocol['end'],protocol['archives'],_complete(root,'development-store'))
        _prepare(root,store,protocol,protocol['test_start'],protocol['end'])
        source = _complete(root,'evaluation-samples')
        if source is None:
            source = _attempt(root,'evaluation-samples')
            build_study_samples(store/'normalized.sqlite',_paths(root,protocol,protocol['end']),source,
                reference,cache=development,corpora=CORPORA)
        rows = read_csv(source/'samples.csv')
        if [r for r in rows if r['label_month']<protocol['test_start']] != read_csv(development/'samples.csv'):
            raise ValueError('Final extension changed the development prefix')
        test = [r for r in rows if r['label_month']>=protocol['test_start']]
        predictions = []
        with threadpool_limits(limits=1):
            for name,item in definitions.items():
                print('prospective evaluate: '+name,flush=True)
                for seed in protocol['seeds']:
                    fitted = joblib.load(selection/f'{name}-{seed}.joblib')
                    if item['kind']=='legacy':
                        guesses,flags = predict_variant(fitted,test)
                        probabilities = [None]*len(test)
                    else:guesses,probabilities,flags = predict_activity_model(fitted,test)
                    for row,guess,probability,flag in zip(test,guesses,probabilities,flags):
                        record = {k:row[k] for k in ('reference_id','feature_month','community_id','label_month','label_reference_id','size')}
                        record.update(model=name,seed=seed,y_true=row['label'],y_pred=guess,
                                      fallback=flag,probabilities=json.dumps(probability))
                        predictions.append(record)
        result = evaluate_activity_predictions(predictions,protocol['seeds'],list(definitions),
            months(protocol['test_start'],protocol['end']),CANDIDATE,protocol['champion'],list(COMPACT_BASELINES),
            protocol['bootstrap_draws'],protocol['block_length'],protocol['bootstrap_seed'])
        # One shared resample inventory compares the fixed primary to every
        # baseline/control. Realized strongest baseline remains descriptive.
        contrasts = summarize([dict(r,model='full' if r['model']==CANDIDATE else r['model']) for r in predictions],
            protocol['seeds'],['full' if n==CANDIDATE else n for n in definitions],
            months(protocol['test_start'],protocol['end']),protocol['bootstrap_draws'],
            protocol['block_length'],protocol['bootstrap_seed'])
        frozen(root)
        output = _attempt(root,'evaluation')
        output.mkdir()
        write_csv(output/'predictions.csv',predictions)
        json_write(output/'evaluation.json',result)
        json_write(output/'contrasts.json',contrasts)
        seal(output,dict(status='complete',stage='evaluation',
            sample_manifest_sha256=digest_file(source/'complete.json'),
            selection_manifest_sha256=digest_file(selection/'complete.json'),
            final_targets_prepared_after_freeze=True,evaluated_utc=datetime.now(timezone.utc).isoformat()))
    elif stage=='review':
        from reddit_sna.evaluation.label_validation import prepare_panel
        if _complete(root,'evaluation') is None:raise ValueError('Complete evaluation before supplement panel')
        output = panel_path(root)
        if output.exists():
            verified(output)
        else:prepare_panel(root,output,'development',protocol['review_per_stratum'],protocol['review_seed'])
    else:raise ValueError('Unknown prospective stage')


def run(protocol_path, root, stage, artifact_root=Path('artifacts')):
    """Run one monitored stage with a declaration written before downloading."""
    root,artifact_root = Path(root).resolve(),Path(artifact_root).resolve()
    if root==artifact_root or not root.is_relative_to(artifact_root) or stage not in STAGES:
        raise ValueError('Prospective run must be a child of artifacts with a known stage')
    protocol,definitions,model_path = load_protocol(protocol_path)
    root.mkdir(parents=True,exist_ok=True)
    declare(root,protocol,definitions,protocol_path,model_path)
    if stage=='evaluate':frozen(root)
    count = len(list((root/'resources').glob(stage+'-*.json')))
    command = [sys.executable,'-X','utf8','-m',__name__,'--worker','--protocol',str(Path(protocol_path).resolve()),
               '--root',str(root),'--stage',stage]
    return monitored(command,root,f'{stage}-{count+1:03d}',protocol)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',action='store_true',required=True)
    parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--stage',choices=STAGES,required=True)
    args=parser.parse_args()
    protocol,definitions,_=load_protocol(args.protocol)
    work(args.root,protocol,definitions,args.stage)
