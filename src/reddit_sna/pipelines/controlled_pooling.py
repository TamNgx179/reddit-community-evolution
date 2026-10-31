"""Finite feature/head experiment on a frozen, already observed research cohort.

No search or primary-model promotion occurs here. The four LR cells distinguish
member means from hierarchy, and two flat HGB controls expose estimator effects.
"""
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
import tomllib
import numpy as np
from threadpoolctl import threadpool_limits

from reddit_sna.config import validate_run_id
from reddit_sna.contracts import next_month
from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.diagnostics import coverage_tables, forecast_tables, paired_tables, prediction_units
from reddit_sna.evaluation.research import KEY, EVENTS, score
from reddit_sna.evaluation.research_protocol import FULL
from reddit_sna.features.member_summary import MEAN_FIELDS, member_mean
from reddit_sna.models.activity_forecast import fit_activity_model, predict_activity_model
from reddit_sna.pipelines.hetco import load_samples
from reddit_sna.pipelines.research import read_table, write_table, save_json

BASELINES = ('B1_majority','B1_persistence','B4_logreg','B2_random_forest','B5_matched_boosting')
CELLS = {
    'LR_flat_community': ('lr',False,False), 'LR_hier_community': ('lr',True,False),
    'LR_flat_member_mean': ('lr',False,True), 'LR_hier_member_mean': ('lr',True,True),
    'HGB_flat_community': ('hgb',False,False), 'HGB_flat_member_mean': ('hgb',False,True)}
LR = dict(estimator='lr', C=1., class_weight='balanced', transform='standard')
HGB = dict(estimator='hgb', max_leaf_nodes=7, min_samples_leaf=20, class_weight='balanced')
PROTOCOL = dict(schema_version=1, protocol_id='member-pooling-factorial-v1',
    exposure='inspected_development_data', test_start='2016-10',
    rolling_months=[f'2016-{m:02}' for m in range(7,13)], seeds=[42,43,44],
    maximum_configuration_fits=126, bootstrap_draws=1000, bootstrap_seed=20261031,
    block_length=2, minimum_block_months=6, candidate='LR_hier_member_mean')


def verify_run(directory, root, filename='manifest.json'):
    """Verify declared payload bytes without loading any saved estimator object."""
    directory,root=Path(directory).resolve(),Path(root).resolve()
    if not directory.is_relative_to(root) or directory==root:
        raise ValueError('Run must be inside artifacts')
    path=directory/filename
    info=json.loads(path.read_text(encoding='utf-8'))
    if info.get('status') not in ('complete','complete_through_detection') or not info.get('artifact_hashes'):
        raise ValueError('Run must be completed with a payload inventory')
    for name,expected in info['artifact_hashes'].items():
        payload=(directory/name).resolve()
        if not payload.is_relative_to(directory) or digest_file(payload)!=expected:
            raise ValueError('Artifact hash mismatch or unsafe inventory path')
    return info


def read_mean_cache(directory, pins):
    """Reject changed means, source bindings and column order before reuse."""
    directory=Path(directory)
    info=json.loads((directory/'cache.json').read_text())
    if (info['source_manifests']!=pins or info['fields']!=list(MEAN_FIELDS)
            or digest_file(directory/'member-means.csv')!=info['sha256']):
        raise ValueError('Member summary cache binding/schema/hash mismatch')
    rows=read_table(directory/'member-means.csv')
    if not rows or list(rows[0])!=list(KEY)+list(MEAN_FIELDS):
        raise ValueError('Member summary cache columns differ')
    keys=[tuple(r[k] for k in KEY) for r in rows]
    if len(set(keys))!=len(keys):
        raise ValueError('Duplicate member summary cache key')
    if any(not np.isfinite(float(r[f])) for r in rows for f in MEAN_FIELDS):
        raise ValueError('Nonfinite member summary cache')
    return {tuple(r[k] for k in KEY):r for r in rows}


def _diagnostics(output, prefix, features, labels, predictions, contrasts, graph=None):
    coverage,distributions=coverage_tables(labels,features,graph)
    metrics,classes,confusion=forecast_tables(predictions,features)
    cases,intervals=paired_tables(predictions,features,contrasts)
    payload=dict(coverage=coverage,distributions=distributions,metrics=metrics,classes=classes,
                 confusion=confusion,paired_cases=cases,intervals=intervals)
    for name,rows in payload.items():
        if rows:
            fields=sorted(set().union(*(r.keys() for r in rows)))
            write_table(output/f'{prefix}-{name}.csv',rows,fields)
    return payload


def run_controlled_pooling(protocol_path, research_run, preparation, artifact_root, run_id,
                           *, original_study=None, hetco_run=None):
    """Freeze the finite schedule before extraction/fit and retain failed attempts."""
    started=perf_counter()
    root=Path(artifact_root).resolve()
    research,preparation=Path(research_run).resolve(),Path(preparation).resolve()
    protocol_path=Path(protocol_path).resolve()
    protocol=tomllib.loads(protocol_path.read_text(encoding='utf-8'))
    if json.dumps(protocol,sort_keys=True)!=json.dumps(PROTOCOL,sort_keys=True):
        raise ValueError('Unsupported controlled-pooling protocol or fit budget')
    validate_run_id(run_id)
    output=root/'controlled-pooling'/run_id
    if output.exists():
        raise FileExistsError('Controlled-pooling output already exists')
    sources=[research,preparation]
    rm=verify_run(research,root); verify_run(preparation,root)
    if Path(rm['source_preparation']).resolve()!=preparation:
        raise ValueError('Research preparation mismatch')
    forecast=Path(rm['source_forecast']).resolve()
    verify_run(forecast,root);sources.append(forecast)
    for name,expected in rm['source_manifests'].items():
        p=Path(name)
        if digest_file(p/'manifest.json' if p.is_dir() else p)!=expected:
            raise ValueError('Research consuming source hash mismatch')
    archived=[]
    if hetco_run is not None:
        h=Path(hetco_run).resolve(); hm=verify_run(h,root);sources.append(h)
        pins_h=hm['source_manifests']
        if (pins_h.get(str(research/'manifest.json'))!=digest_file(research/'manifest.json')
                or pins_h.get(str(preparation/'manifest.json'))!=digest_file(preparation/'manifest.json')):
            raise ValueError('HeTCo sources do not match the controlled cohort')
        archived=read_table(h/'predictions.csv')
    originals=[]; original_graph={}; extra_pins={}
    if original_study is not None:
        study=Path(original_study).resolve()
        # Match attempts through consuming metadata, not by assuming first success.
        freeze=json.loads((study/'freeze.json').read_text())
        evals=list((study/'stages/evaluation').glob('attempt-*/complete.json'))
        matches=[p for p in evals if json.loads(p.read_text()).get('selection_manifest_sha256')==freeze['selection_manifest_sha256']]
        if len(matches)!=1:
            raise ValueError('Original evaluation must have one declared consuming attempt')
        ep=matches[0].parent; em=verify_run(ep,root,'complete.json')
        sample_paths=list((study/'stages/evaluation-samples').glob('attempt-*/complete.json'))
        matches=[p for p in sample_paths if digest_file(p)==em['sample_manifest_sha256']]
        if len(matches)!=1:
            raise ValueError('Original sample manifest mismatch')
        sp=matches[0].parent;verify_run(sp,root,'complete.json')
        originals=[ep,sp]
        selection=(study/freeze['selection']).resolve()
        if digest_file(selection/'complete.json')!=freeze['selection_manifest_sha256']:
            raise ValueError('Original selection manifest mismatch')
        extra_pins[str(study/'freeze.json')]=digest_file(study/'freeze.json')
        extra_pins[str(selection/'complete.json')]=digest_file(selection/'complete.json')
        for month,expected in json.loads((sp/'complete.json').read_text())['input_month_manifests'].items():
            paths=[p for p in (study/f'stages/month-{month}').glob('attempt-*/complete.json') if digest_file(p)==expected]
            if len(paths)!=1:
                raise ValueError('Original monthly consuming manifest mismatch')
            source=paths[0].parent
            info=json.loads(paths[0].read_text())
            graph_path=source/'snapshots.json'
            if digest_file(graph_path)!=info['artifact_hashes']['snapshots.json']:
                raise ValueError('Original graph observation metadata changed')
            original_graph[month]=json.loads(graph_path.read_text())['months'][0]
            extra_pins[str(paths[0])]=digest_file(paths[0])
            extra_pins[str(graph_path)]=digest_file(graph_path)
    if (not output.resolve().is_relative_to(root)
            or any(output.is_relative_to(s) or s.is_relative_to(output) for s in sources+originals)):
        raise ValueError('Output overlaps its inputs or escapes artifacts')
    pins={str(s/'manifest.json'):digest_file(s/'manifest.json') for s in sources}
    pins.update({str(s/'complete.json'):digest_file(s/'complete.json') for s in originals})
    pins.update(extra_pins)
    pins[str(protocol_path)]=digest_file(protocol_path)
    package=Path(__file__).parents[1]
    code={p.relative_to(package).as_posix():digest_file(p) for p in package.rglob('*.py')}
    samples=read_table(research/'samples.csv')
    keys=[tuple(r[k] for k in KEY) for r in samples]
    if not samples or len(set(keys))!=len(keys) or any(r['label_month']!=next_month(r['feature_month']) or r['label'] not in EVENTS for r in samples):
        raise ValueError('Samples require unique full keys and consecutive target months')
    if any(not '2016-01'<=r['feature_month']<='2016-11' or r['label_month']>'2016-12' for r in samples):
        raise ValueError('This diagnostic protocol is restricted to the declared 2016 cohort')
    baselines=[r for r in read_table(research/'predictions.csv') if r['model'] in BASELINES]
    if {r['model'] for r in baselines}!=set(BASELINES):
        raise ValueError('All five stored baseline controls are required')
    prediction_units(baselines+archived)
    labels=read_table(forecast/'labels.csv'); features=read_table(forecast/'features.csv')
    feature_map={tuple(r[k] for k in KEY[:3]):r for r in features}
    label_map={tuple(r[k] for k in KEY):r for r in labels}
    if len(label_map)!=len(labels):
        raise ValueError('Duplicate frozen label key')
    coverage_tables(labels,features)
    for r in samples:
        key=tuple(r[k] for k in KEY)
        if key not in label_map or label_map[key]['label']!=r['label'] or str(label_map[key]['eligible'])!='1':
            raise ValueError('Samples differ from frozen target labels')
        f=feature_map.get(key[:3])
        if f is None or any(not np.isclose(float(r[name]),float(f[name]),rtol=1e-12,atol=1e-12) for name in FULL if name in f):
            raise ValueError('Research community features differ from the source forecast')
    windows=[('main',protocol['test_start'])]+[('rolling',m) for m in protocol['rolling_months']]
    # Preflight all expected test/training inventories before extraction or fitting.
    base_units=prediction_units(baselines)
    if set(base_units)!={(w,m,s) for w in ('main','rolling') for m in BASELINES for s in protocol['seeds']}:
        raise ValueError('Incomplete baseline model/seed/window inventory')
    for window in ('main','rolling'):
        expected={tuple(r[k] for k in KEY) for r in samples if r['label_month']>=protocol['test_start']} if window=='main' else {tuple(r[k] for k in KEY) for r in samples if r['label_month'] in protocol['rolling_months']}
        if any(set(rows)!=expected for u,rows in base_units.items() if u[0]==window):
            raise ValueError('Baseline window keys differ from declared samples')
    if any(not any(r['label_month']<boundary for r in samples) or not any(r['label_month']==boundary for r in samples) for _,boundary in windows):
        raise ValueError('Every origin requires nonempty causal train and test data')
    output.mkdir(parents=True)
    manifest=dict(status='started',artifact_type='controlled-pooling-v1',protocol=protocol,
        cells={k:list(v) for k,v in CELLS.items()},source_manifests=pins,source_hashes=code,
        community_fields=list(FULL),member_fields=list(MEAN_FIELDS),settings=dict(lr=LR,hgb=HGB),
        exposure='inspected_development_data',unseen=False,human_annotation='pending',
        primary_promotion=False,created_utc=datetime.now(timezone.utc).isoformat(),configuration_fits=0)
    save_json(output/'manifest.json',manifest)
    save_json(output/'protocol.json',dict(**protocol,cells=manifest['cells'],settings=manifest['settings']))
    fits=[]
    try:
        print('Extracting causal member summaries once',flush=True)
        bags=load_samples(research,preparation,extended=True)
        means=[dict(**{k:r[k] for k in KEY},**member_mean(r['bag_extended'])) for r in bags]
        write_table(output/'member-means.csv',means,list(KEY)+list(MEAN_FIELDS))
        save_json(output/'cache.json',dict(source_manifests=pins,fields=list(MEAN_FIELDS),sha256=digest_file(output/'member-means.csv')))
        cache=read_mean_cache(output,pins)
        if set(cache)!=set(keys):
            raise ValueError('Member means differ from the sample inventory')
        for r in samples:
            r.update({f:float(cache[tuple(r[k] for k in KEY)][f]) for f in MEAN_FIELDS})
        write_table(output/'samples.csv',samples)
        del bags
        predictions=[]
        with threadpool_limits(limits=1):
            for window,boundary in windows:
                train=[r for r in samples if r['label_month']<boundary]
                test=[r for r in samples if (r['label_month']>=boundary if window=='main' else r['label_month']==boundary)]
                for seed in protocol['seeds']:
                    for name,(estimator,hierarchical,members) in CELLS.items():
                        if len(fits)>=protocol['maximum_configuration_fits']:
                            raise ValueError('Declared fit budget exhausted')
                        tick=perf_counter()
                        fields=FULL+MEAN_FIELDS if members else FULL
                        fitted=fit_activity_model(train,fields,LR if estimator=='lr' else HGB,hierarchical,seed)
                        guesses,probabilities,flags=predict_activity_model(fitted,test)
                        fits.append(dict(window=window,boundary=boundary,seed=seed,model=name,train_n=len(train),test_n=len(test),
                            latest_train_label=max(r['label_month'] for r in train),internal_heads=2 if hierarchical else 1,
                            fallback=bool(fitted['fallback']),wall_seconds=perf_counter()-tick))
                        predictions.extend(dict(**{k:r[k] for k in KEY},window=window,model=name,seed=seed,
                            y_true=r['label'],y_pred=p,fallback=f,**{f'p_{e}':float(v) for e,v in zip(EVENTS,prob)})
                            for r,p,prob,f in zip(test,guesses,probabilities,flags))
                        save_json(output/'fits.json',fits)
                        print(f'{len(fits)}/126 {window} {boundary} {seed} {name}',flush=True)
        if len(fits)!=protocol['maximum_configuration_fits']:
            raise ValueError('Incomplete declared experiment')
        write_table(output/'predictions.csv',predictions)
        combined=baselines+archived+predictions
        prediction_units(combined)
        units=prediction_units(combined)
        comparison=[]
        for window in ('main','rolling'):
            for model in sorted({u[1] for u in units if u[0]==window}):
                values=[score(list(units[(window,model,s)].values())) for s in protocol['seeds']]
                comparison.append(dict(window=window,model=model,n=values[0]['n'],
                    macro_f1_six=float(np.mean([v['macro_f1_six'] for v in values])),
                    seed_sd=float(np.std([v['macro_f1_six'] for v in values],ddof=1))))
        write_table(output/'comparison.csv',comparison)
        contrasts=[('LR_hier_member_mean','LR_hier_community'),('LR_flat_member_mean','LR_flat_community'),
                   ('LR_hier_member_mean','LR_flat_member_mean'),('HGB_flat_member_mean','HGB_flat_community')]
        contrasts += [('LR_hier_member_mean',m) for m in BASELINES]
        graph={r['month']:r for r in json.loads((preparation/'snapshots.json').read_text())['months']}
        _diagnostics(output,'replication',features,labels,combined,contrasts,graph)
        if originals:
            ep,sp=originals
            old=[r for r in read_table(ep/'predictions.csv') if r['model'] in ('hier_lr_dynamic','hier_hgb_dynamic','A_no_dynamics_matched','A_flat_matched')]
            _diagnostics(output,'original',read_table(sp/'features.csv'),read_table(sp/'labels.csv'),old,
                [('hier_lr_dynamic','hier_hgb_dynamic'),('hier_lr_dynamic','A_no_dynamics_matched'),('hier_lr_dynamic','A_flat_matched')],original_graph)
        if any(digest_file(Path(p))!=h for p,h in pins.items()) or code!={p.relative_to(package).as_posix():digest_file(p) for p in package.rglob('*.py')}:
            raise ValueError('Pinned source/configuration changed during the run')
        # Reread critical source inventories before claiming completion.
        for s in sources: verify_run(s,root)
        for s in originals: verify_run(s,root,'complete.json')
        manifest.update(status='complete',configuration_fits=len(fits),internal_heads=sum(r['internal_heads'] for r in fits),
                        wall_seconds=perf_counter()-started,finished_utc=datetime.now(timezone.utc).isoformat())
    except BaseException as exc:
        manifest.update(status='failed',failure_type=type(exc).__name__,configuration_fits=len(fits))
        raise
    finally:
        manifest['artifact_hashes']={p.relative_to(output).as_posix():digest_file(p) for p in output.rglob('*') if p.is_file() and p.name!='manifest.json'}
        save_json(output/'manifest.json',manifest)
    return output
