"""Actual synthetic raw-to-freeze/evaluation checks, never performance evidence."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from sklearn.metrics import f1_score

from reddit_sna.data.archive import digest_file
from reddit_sna.data.confirmation import CORPORA
from reddit_sna.data.normalize import month_boundary
from reddit_sna.data.study import normalize_study
from reddit_sna.evaluation.label_validation import LABELS, prepare_panel, summarize_panel
from reddit_sna.evaluation.temporal_protocol import COMPACT_MODELS, EVENTS, months
from reddit_sna.pipelines.confirmation import frozen, load_protocol, run_confirmation, worker
from reddit_sna.pipelines.study_preparation import seal, verified
from reddit_sna.pipelines.study_samples import build_study_samples, read_csv
from reddit_sna.pipelines.temporal_study import _attempt, _complete
from reddit_sna.reporting.confirmation import confirmation_figures, read_confirmation, render_confirmation
from reddit_sna.reporting.temporal_study import read_study

PROJECT=Path(__file__).parents[2]
PROTOCOL=PROJECT/'configs/confirmation.toml'


def archives(raw):
    raw.mkdir()
    for i,corpus in enumerate(CORPORA):
        records=[]
        for month in months('2015-01','2018-10'):
            key=f'p{i}_{month}'
            records.append(dict(id='t3_'+key,root=key,reply_to=None,user='Alice' if i==0 else f'Isolate{i}',
                                timestamp=month_boundary(month)))
            if i==0:
                records.append(dict(id='t1_'+key,root=key,reply_to='t3_'+key,user='Bob',
                                    timestamp=month_boundary(month)+1))
        with zipfile.ZipFile(raw/f'{corpus}.corpus.zip','w') as archive:
            archive.writestr('utterances.jsonl','\n'.join(json.dumps(r) for r in records)+'\n')


class ConfirmationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.base=Path(cls.temp.name)
        cls.artifacts=cls.base/'artifacts';cls.root=cls.artifacts/'external'
        try:run_confirmation(PROTOCOL,cls.root,'evaluate',cls.artifacts)
        except FileNotFoundError:cls.blocked=True
        else:cls.blocked=False
        archives(cls.root/'raw')
        cls.protocol,_,cls.definitions,_=load_protocol(PROTOCOL)
        worker(cls.root,cls.protocol,cls.definitions,'develop')
        cls.no_final_before_fit=_complete(cls.root,'month-2018-01') is None
        worker(cls.root,cls.protocol,cls.definitions,'fit')
        cls.freeze_bytes=(cls.root/'freeze.json').read_bytes()
        worker(cls.root,cls.protocol,cls.definitions,'evaluate')

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_full_pipeline_matched_population_fixed_six_class_and_negative_result(self):
        self.assertTrue(self.blocked);self.assertTrue(self.no_final_before_fit)
        data=read_study(self.root)
        self.assertEqual(tuple(data['selection']['models']),COMPACT_MODELS)
        self.assertEqual(len(data['graph_scale']),45)
        self.assertEqual(len(data['evaluation']['metrics']),21)
        self.assertEqual(data['evaluation']['superiority'],'not_demonstrated')
        self.assertFalse(data['exposure']['independent_users'])
        self.assertEqual(data['selection']['latest_training_label'],'2017-12')
        self.assertEqual(data['corpora'],list(CORPORA))
        # Stable-only data must score 1/6, not an inflated single-class score 1.
        for name in COMPACT_MODELS:
            rows=[r for r in data['predictions'] if r['model']==name and int(r['seed'])==42]
            score=f1_score([r['y_true'] for r in rows],[r['y_pred'] for r in rows],labels=list(EVENTS),average='macro',zero_division=0)
            self.assertAlmostEqual(data['evaluation']['mean_macro_f1'][name],score)
            self.assertAlmostEqual(score,1/6)
        self.assertEqual((self.root/'freeze.json').read_bytes(),self.freeze_bytes)

    def test_source_model_protocol_and_sample_drift_are_refused(self):
        selection,development=frozen(self.root)
        paths=[next(selection.glob('*.joblib')),development/'features.csv',self.root/'protocol.json',self.root/'freeze.json']
        for path in paths:
            saved=path.read_bytes()
            try:
                if path.name=='freeze.json':
                    value=json.loads(saved);value['critical_source_hashes']['features/context.py']='changed'
                    path.write_text(json.dumps(value))
                else:path.write_bytes(saved+b'changed')
                with self.assertRaises((ValueError,json.JSONDecodeError)):frozen(self.root)
            finally:path.write_bytes(saved)
        frozen(self.root)

    def test_future_record_perturbation_and_cache_cohort_binding(self):
        source=_complete(self.root,'development-samples')
        info=verified(source)
        directories={month:_complete(self.root,f'month-{month}') for month in info['months']}
        # Normalize an archive with arbitrary 2018+ activity changed. Every
        # pre-2018 metadata row remains identical under the cutoff adapter.
        raw=self.base/'perturbed-raw';archives(raw)
        first=raw/f'{CORPORA[0]}.corpus.zip'
        with zipfile.ZipFile(first) as archive:lines=archive.read('utterances.jsonl').decode().splitlines()
        rows=[json.loads(line) for line in lines]
        for row in rows:
            if row['timestamp']>=month_boundary('2018-01'):row['user']='FutureChanged'
        with zipfile.ZipFile(first,'w') as archive:archive.writestr('utterances.jsonl','\n'.join(json.dumps(r) for r in rows)+'\n')
        db=self.base/'perturbed.sqlite'
        normalize_study(sorted(raw.glob('*.zip')),db,'2018-01',progress=lambda *a,**k:None)
        rebuilt=self.base/'rebuilt'
        build_study_samples(db,directories,rebuilt,info['reference_id'],corpora=CORPORA)
        self.assertEqual((source/'features.csv').read_bytes(),(rebuilt/'features.csv').read_bytes())
        self.assertEqual((source/'samples.csv').read_bytes(),(rebuilt/'samples.csv').read_bytes())
        with self.assertRaisesRegex(ValueError,'normalization'):
            build_study_samples(db,directories,self.base/'wrong-context',info['reference_id'])
        # Simulate the first-version manifest without context_corpora; sealed
        # graph inventories still bind its normalization. Never alter real runs.
        cache=self.base/'old-cache'
        import shutil
        shutil.copytree(source,cache)
        meta=json.loads((cache/'complete.json').read_text());meta.pop('context_corpora')
        (cache/'complete.json').unlink();seal(cache,{k:v for k,v in meta.items() if k!='artifact_hashes'})
        allmonths={month:_complete(self.root,f'month-{month}') for month in months('2015-01','2018-10')}
        output=self.base/'old-cache-extended'
        build_study_samples(_complete(self.root,'evaluation-store')/'normalized.sqlite',allmonths,
            output,info['reference_id'],cache=cache,corpora=CORPORA)
        self.assertEqual(read_csv(output/'samples.csv'),read_csv(_complete(self.root,'evaluation-samples')/'samples.csv'))
        meta=json.loads((cache/'complete.json').read_text());meta['context_corpora']=['wrong','normalization']
        (cache/'complete.json').unlink();seal(cache,{k:v for k,v in meta.items() if k!='artifact_hashes'})
        with self.assertRaisesRegex(ValueError,'normalization'):
            build_study_samples(db,allmonths,self.base/'invalid-cache',info['reference_id'],cache=cache,corpora=CORPORA)

    def test_deterministic_blinded_panels_and_honest_report_figures(self):
        review=self.base/'review'
        for period in ('development','final'):
            panel=review/period;copy=review/f'{period}-copy'
            a=prepare_panel(self.root,panel,period,per_stratum=3)
            b=prepare_panel(self.root,copy,period,per_stratum=3)
            self.assertEqual(a['payload_sha256'],b['payload_sha256'])
            cases=json.loads((panel/'reviewer/cases.json').read_text())
            self.assertEqual(len(cases),3)
            for case in cases:
                self.assertNotIn('label',case);self.assertNotIn('stratum',case)
                self.assertEqual(case['label_month']<'2018-01',period=='development')
            paths=[]
            for index in (1,2):
                path=review/f'{period}-{index}.json';paths.append(path)
                path.write_text(json.dumps(dict(reviewer_id=f'fixture-{index}',reviewer_type='automated',
                    provenance='Synthetic integration fixture, not research evidence',payload_sha256=a['payload_sha256'],
                    submitted_utc='2026-10-23T00:00:00+00:00',
                    attestations=dict(answer_key_not_seen=True,predictions_not_seen=True,other_assessment_not_seen=True),
                    judgments=[dict(case_id=c['case_id'],label='stable',confidence='medium',rationale='Synthetic equal-size fixture') for c in cases])))
            summarize_panel(panel,*paths,review/f'{period}-result')
        data=read_confirmation(self.root,self.root,review)
        text=render_confirmation(data)
        for claim in ('supplementary automated','Human review remains pending','not_demonstrated','users may overlap','no new hyperparameter search'):
            self.assertIn(claim,text)
        import matplotlib.pyplot as plt
        figures=confirmation_figures(data)
        self.assertEqual(set(figures),{'comparison','monthly','support'})
        for figure in figures.values():
            self.assertTrue(figure.axes);plt.close(figure)

    def test_unsafe_root_and_changed_declaration_are_refused(self):
        with self.assertRaises(ValueError):run_confirmation(PROTOCOL,self.base/'outside','develop',self.artifacts)
        path=self.root/'declaration.json';saved=path.read_bytes()
        try:
            value=json.loads(saved);value['models']['champion']='B1_majority';path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'declaration changed'):
                run_confirmation(PROTOCOL,self.root,'develop',self.artifacts)
        finally:path.write_bytes(saved)


if __name__=='__main__':unittest.main()
