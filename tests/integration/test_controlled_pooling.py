"""Real SQLite/CSV synthetic end-to-end experiment and artifact failure paths."""
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import numpy as np
from reddit_sna.cli import main
from reddit_sna.contracts import next_month
from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.research import KEY, EVENTS
from reddit_sna.evaluation.research_protocol import FULL
from reddit_sna.pipelines.controlled_pooling import BASELINES, CELLS, run_controlled_pooling, read_mean_cache
from reddit_sna.pipelines.research import write_table, read_table
from reddit_sna.reporting.diagnostics import export_figures, write_report, read_diagnostics

CONFIG=Path(__file__).resolve().parents[2]/'configs/controlled_pooling.toml'


def seal(path,**extra):
    info=dict(status='complete',artifact_hashes={p.relative_to(path).as_posix():digest_file(p) for p in path.rglob('*') if p.is_file() and p.name!='manifest.json'},**extra)
    (path/'manifest.json').write_text(json.dumps(info))


def fixture(root):
    """Twelve small synthetic snapshots, not Reddit measurements."""
    prep=root/'prepared';research=root/'research';forecast=root/'forecast'
    for p in (prep,research,forecast):p.mkdir()
    db=sqlite3.connect(prep/'normalized.sqlite')
    db.execute('CREATE TABLE records(id TEXT PRIMARY KEY,user_id TEXT,root TEXT,parent TEXT,timestamp REAL,month TEXT,kind TEXT,corpus TEXT)')
    samples=[];features=[];labels=[];graphs=[];record=0
    for m in range(1,13):
        month=f'2016-{m:02}';members=[];edges=[]
        for c in range(4):
            users=[f'u{c}-{i}' for i in range(c+2)]
            members.extend(dict(reference_id='r',month=month,community_id=f'c{c}',user_id=u) for u in users)
            edges.extend(dict(month=month,source_user_id=a,target_user_id=b,weight=c+1) for a,b in zip(users,users[1:]))
            for u in users:
                record+=1;db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?,?)',(str(record),u,'root',None,0,month,'comment','X'))
            f=dict(reference_id='r',feature_month=month,community_id=f'c{c}',available_through_month=month,
                   **{field:float(c+1) for field in FULL})
            f.update(size=c+2,density=2/(c+2),history_missing=int(m==1),community_age=m)
            features.append(f)
            if m<12:
                key=dict(reference_id='r',feature_month=month,community_id=f'c{c}',label_month=next_month(month),label_reference_id='l')
                label=EVENTS[(m+c)%6]
                labels.append(dict(**key,label=label,eligible=1,reason='synthetic_known_rule'))
                samples.append(dict(**key,**{field:f[field] for field in FULL},label=label,past_event=''))
        for folder,rows in ((prep/f'memberships/{month}',members),(prep/f'snapshots/{month}',edges)):
            folder.mkdir(parents=True)
            write_table(folder/('membership-seed0.csv' if 'memberships' in folder.parts else 'R.csv'),rows)
        write_table(prep/f'snapshots/{month}/directed_R.csv',edges)
        graphs.append(dict(month=month,reply_endpoints=14,observed_users=16,
                           reply_coverage_observed_users=14/16,reply_coverage_active_authors=1.))
    db.commit();db.close()
    (prep/'detection.json').write_text(json.dumps(dict(canonical_seed=0)))
    (prep/'snapshots.json').write_text(json.dumps(dict(months=graphs)))
    seal(prep)
    write_table(forecast/'features.csv',features);write_table(forecast/'labels.csv',labels)
    seal(forecast)
    write_table(research/'samples.csv',samples)
    predictions=[]
    for window in ('main','rolling'):
        for model in BASELINES:
            for seed in (42,43,44):
                predictions.extend(dict(**{k:r[k] for k in KEY},window=window,model=model,seed=seed,y_true=r['label'],y_pred='dissolve',fallback=0)
                    for r in samples if r['label_month']>=('2016-10' if window=='main' else '2016-07'))
    write_table(research/'predictions.csv',predictions)
    seal(research,source_preparation=str(prep.resolve()),source_forecast=str(forecast.resolve()),
         source_manifests={str(prep/'manifest.json'):digest_file(prep/'manifest.json'),str(forecast/'manifest.json'):digest_file(forecast/'manifest.json')})
    return prep,research,forecast


class ControlledPoolingTests(unittest.TestCase):
    def test_real_synthetic_run_cache_predictions_report_and_figures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);prep,research,forecast=fixture(root)
            before=digest_file(prep/'manifest.json')
            output=run_controlled_pooling(CONFIG,research,prep,root,'synthetic')
            data=read_diagnostics(output);manifest=data['manifest']
            self.assertEqual(manifest['configuration_fits'],126);self.assertEqual(manifest['internal_heads'],168)
            self.assertEqual(manifest['human_annotation'],'pending');self.assertFalse(manifest['primary_promotion'])
            fits=json.loads((output/'fits.json').read_text())
            self.assertTrue(all(r['latest_train_label']<r['boundary'] for r in fits))
            predictions=read_table(output/'predictions.csv')
            self.assertEqual({r['model'] for r in predictions},set(CELLS))
            self.assertTrue(all(np.isclose(sum(float(r[f'p_{e}']) for e in EVENTS),1.) for r in predictions))
            export_figures(output,root/'figures');self.assertEqual(len(list((root/'figures').glob('*.png'))),4)
            report=write_report(output,root/'report.md').read_text()
            self.assertIn('pending genuine submissions',report);self.assertIn('126 configuration fits',report)
            self.assertEqual(digest_file(prep/'manifest.json'),before)
            with self.assertRaises(FileExistsError):run_controlled_pooling(CONFIG,research,prep,root,'synthetic')
            (output/'member-means.csv').write_text('tampered')
            with self.assertRaises(ValueError):read_mean_cache(output,manifest['source_manifests'])
            with self.assertRaises(ValueError):read_diagnostics(output)

    def test_changed_input_hash_and_cli_are_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);prep,research,_=fixture(root)
            (research/'samples.csv').write_text('changed')
            with self.assertRaises(ValueError):run_controlled_pooling(CONFIG,research,prep,root,'bad')
            self.assertFalse((root/'controlled-pooling/bad').exists())
            with contextlib.redirect_stderr(io.StringIO()),contextlib.redirect_stdout(io.StringIO()):
                code=main(['controlled-pooling','--protocol',str(CONFIG),'--research-run',str(research),
                           '--preparation-run',str(prep),'--artifact-root',str(root),'--run-id','bad'])
            self.assertEqual(code,2)

    def test_declared_budget_cannot_be_expanded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'protocol.toml'
            config.write_text(CONFIG.read_text().replace('126','127'))
            with self.assertRaisesRegex(ValueError,'protocol'):
                run_controlled_pooling(config,root/'missing',root/'missing',root,'bad')

    def test_bad_reference_and_missing_seed_fail_before_extraction(self):
        for mutation in ('reference','seed'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);prep,research,_=fixture(root)
                if mutation=='reference':
                    rows=read_table(research/'samples.csv');rows[0]['label_reference_id']='wrong'
                    write_table(research/'samples.csv',rows)
                else:
                    rows=[r for r in read_table(research/'predictions.csv') if r['seed']!='44']
                    write_table(research/'predictions.csv',rows)
                metadata=json.loads((research/'manifest.json').read_text())
                metadata.pop('status');metadata.pop('artifact_hashes');seal(research,**metadata)
                with self.assertRaises(ValueError):run_controlled_pooling(CONFIG,research,prep,root,'bad')
                self.assertFalse((root/'controlled-pooling/bad').exists())

    def test_extraction_failure_preserves_failed_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);prep,research,_=fixture(root)
            # A genuinely malformed but resealed upstream membership fails in
            # the real extractor. No mocked service or fake success is used.
            rows=read_table(research/'samples.csv');rows[0]['community_id']='absent'
            write_table(research/'samples.csv',rows)
            # Force real extraction failure after preflight using invalid data
            # type in an otherwise hash-consistent directed edge.
            edge=prep/'snapshots/2016-01/R.csv'
            edge.write_text(edge.read_text().replace(',1\n',',not-a-number\n'))
            seal(prep)
            meta=json.loads((research/'manifest.json').read_text());meta.pop('status');meta.pop('artifact_hashes')
            meta['source_manifests'][str(prep/'manifest.json')]=digest_file(prep/'manifest.json')
            # Restore sample identity so the failure reaches extraction.
            rows[0]['community_id']='c0';write_table(research/'samples.csv',rows);seal(research,**meta)
            with self.assertRaises(ValueError):run_controlled_pooling(CONFIG,research,prep,root,'failed')
            self.assertEqual(json.loads((root/'controlled-pooling/failed/manifest.json').read_text())['status'],'failed')
