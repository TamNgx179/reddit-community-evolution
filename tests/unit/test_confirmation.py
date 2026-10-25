"""Measurement, provenance and archive failure controls for confirmation."""

from copy import deepcopy
from contextlib import closing
from io import BytesIO
import json
import math
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from sklearn.metrics import cohen_kappa_score

from reddit_sna.data.archive import CORPORA as ORIGINAL_CORPORA, digest_file
from reddit_sna.data.confirmation import CORPORA, acquire, declared_paths
from reddit_sna.evaluation.label_validation import LABELS, coverage_audit, summarize_panel
from reddit_sna.features.context import context_features
from reddit_sna.pipelines.study_preparation import seal


def dump(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')


def panel_fixture(root, labels=('stable','grow','unresolved')):
    """Synthetic reviewer inputs are test fixtures, not actual annotations."""
    panel=root/'panel';cases=[dict(case_id=str(i)) for i in range(len(labels))]
    dump(panel/'reviewer/cases.json',cases)
    payload=digest_file(panel/'reviewer/cases.json')
    dump(panel/'coordinator/answers.json',[
        dict(case_id=str(i),label=label if label!='unresolved' else '',stratum=label)
        for i,label in enumerate(labels)])
    dump(panel/'manifest.json',dict(cases=len(cases),payload_sha256=payload,source_manifest_sha256='synthetic'))
    seal(panel,dict(status='complete',stage='review-panel'))
    records=[]
    for reviewer in ('fixture-1','fixture-2'):
        records.append(dict(reviewer_id=reviewer,reviewer_type='automated',
            provenance='Synthetic unit-test fixture, not research evidence',payload_sha256=payload,
            submitted_utc='2026-10-23T00:00:00+00:00',
            attestations=dict(answer_key_not_seen=True,predictions_not_seen=True,other_assessment_not_seen=True),
            judgments=[dict(case_id=str(i),label=label,confidence='medium',rationale='Fixture rationale')
                       for i,label in enumerate(labels)]))
    return panel,records


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.panel,self.records=panel_fixture(self.root)

    def summarize(self, records=None, adjudication=None):
        records=records or self.records
        first=self.root/'first.json';second=self.root/'second.json'
        dump(first,records[0]);dump(second,records[1])
        return summarize_panel(self.panel,first,second,self.root/'result',adjudication)

    def test_actual_aggregate_matches_sklearn_and_keeps_discrepancies(self):
        self.records[1]['judgments'][1]['label']='shrink'
        result=self.summarize()
        self.assertAlmostEqual(result['raw_agreement'],2/3)
        self.assertAlmostEqual(result['cohen_kappa'],cohen_kappa_score(
            ['stable','grow','unresolved'],['stable','shrink','unresolved']))
        self.assertEqual(result['human_review'],'pending')
        self.assertFalse(result['independent_human_validation'])
        self.assertEqual(result['confusion'][LABELS.index('grow')][LABELS.index('shrink')],1)
        self.assertEqual(result['adjudication'],'not_submitted')
        self.assertEqual((self.root/'result/first.json').read_bytes(),(self.root/'first.json').read_bytes())

    def test_invalid_submissions_never_create_completed_result(self):
        mutations=[
            lambda r:r[0]['judgments'].pop(),
            lambda r:r[0]['judgments'].append(deepcopy(r[0]['judgments'][0])),
            lambda r:r[0]['judgments'][0].update(case_id='unknown'),
            lambda r:r[0]['judgments'][0].update(label='invented'),
            lambda r:r[0]['judgments'][0].update(confidence=''),
            lambda r:r[0]['judgments'][0].update(rationale=' '),
            lambda r:r[0].update(provenance=''),
            lambda r:r[0].update(submitted_utc='invented'),
            lambda r:r[0].update(submitted_utc='2026-10-23T00:00:00'),
            lambda r:r[0].update(payload_sha256='changed'),
            lambda r:r[0]['attestations'].update(answer_key_not_seen=False),
            lambda r:r[1].update(reviewer_id=r[0]['reviewer_id']),
            lambda r:r[1].update(reviewer_type='human'),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                records=deepcopy(self.records);mutation(records)
                with self.assertRaises(ValueError):self.summarize(records)
                self.assertFalse((self.root/'result').exists())

    def test_changed_panel_fails_before_accepting_submissions(self):
        (self.panel/'coordinator/answers.json').write_text('[]')
        with self.assertRaises(ValueError):self.summarize()

    def test_one_class_kappa_is_explicitly_undefined(self):
        for record in self.records:
            for row in record['judgments']:row['label']='unresolved'
        result=self.summarize()
        self.assertIsNone(result['cohen_kappa']);self.assertEqual(result['raw_agreement'],1)

    def test_empty_panel_is_not_complete_agreement(self):
        base=self.root/'empty';panel,records=panel_fixture(base,())
        dump(base/'a.json',records[0]);dump(base/'b.json',records[1])
        with self.assertRaisesRegex(ValueError,'Empty'):
            summarize_panel(panel,base/'a.json',base/'b.json',base/'result')

    def test_separate_adjudicator_covers_only_real_disagreements(self):
        self.records[1]['judgments'][1]['label']='shrink'
        adjudication=dict(reviewer_id='fixture-3',reviewer_type='automated',
            provenance='Synthetic separate test adjudicator',submitted_utc='2026-10-23T00:00:00+00:00',
            payload_sha256=self.records[0]['payload_sha256'],
            judgments=[dict(case_id='1',label='unresolved',rationale='Ambiguous fixture')])
        path=self.root/'adjudication.json';dump(path,adjudication)
        result=self.summarize(adjudication=path)
        self.assertEqual(result['adjudication']['disagreements'],1)
        self.assertEqual(result['human_review'],'pending')

    def test_same_identity_cannot_adjudicate(self):
        path=self.root/'adjudication.json'
        dump(path,dict(reviewer_id='fixture-1',reviewer_type='automated',
            payload_sha256=self.records[0]['payload_sha256']))
        with self.assertRaisesRegex(ValueError,'separate'):self.summarize(adjudication=path)


class CoverageTests(unittest.TestCase):
    def test_split_month_size_censor_and_development_only_tolerance(self):
        rows=[dict(feature_month='2017-05',label_month='2017-06',community_id='a',
                   label='grow',reason='one_to_one_size_comparison',size='20'),
              dict(feature_month='2017-06',label_month='2017-07',community_id='b',
                   label='',reason='weak_overlap',size='21'),
              dict(feature_month='2018-01',label_month='2018-02',community_id='c',
                   label='stable',reason='one_to_one_size_comparison',size='2'),
              dict(feature_month='2018-09',label_month='2018-10',community_id='d',
                   label='',reason='final_snapshot_censored',size='2')]
        pair=dict(feature_month='2017-05',source_community_id='a',target_community_id='b',accepted='1')
        result=coverage_audit(rows,[pair])
        self.assertEqual(result['periods']['train']['resolved'],1)
        self.assertEqual(result['periods']['validation']['labels']['unresolved'],1)
        self.assertEqual(result['periods']['final']['censored'],1)
        self.assertEqual(result['periods']['final']['observed_transitions'],1)
        self.assertEqual(result['monthly']['2018-02']['sizes']['stable:le2'],1)
        self.assertEqual(result['near_stability']['counts'],{'0.0':0,'0.05':1,'0.1':1})
        self.assertEqual(result['near_stability']['one_to_one_cases'],1)
        with self.assertRaisesRegex(ValueError,'Duplicate'):coverage_audit(rows+rows[:1])


class ContextCohortTests(unittest.TestCase):
    def test_old_default_equivalence_new_entropy_and_future_invariance(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'data.sqlite'
            from reddit_sna.data.normalize import month_boundary
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('CREATE TABLE records(user_id TEXT,root TEXT,corpus TEXT,timestamp REAL,month TEXT)')
                db.executemany('INSERT INTO records VALUES(?,?,?,?,?)',[
                    ('u','r',corpus,month_boundary('2017-01'),'2017-01') for corpus in ORIGINAL_CORPORA[:2]])
            groups={'g':{'u'}}
            old=context_features(path,'2017-01',groups)
            self.assertEqual(old,context_features(path,'2017-01',groups,corpora=ORIGINAL_CORPORA))
            self.assertAlmostEqual(old['g']['subreddit_entropy'],math.log(2)/math.log(15))
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('DELETE FROM records')
                db.executemany('INSERT INTO records VALUES(?,?,?,?,?)',[
                    ('u','r',corpus,month_boundary('2017-01'),'2017-01') for corpus in CORPORA])
            before=context_features(path,'2017-01',groups,corpora=CORPORA)
            self.assertAlmostEqual(before['g']['subreddit_entropy'],1)
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('INSERT INTO records VALUES(?,?,?,?,?)',('future','r',CORPORA[0],month_boundary('2018-01'),'2018-01'))
            self.assertEqual(before,context_features(path,'2017-01',groups,corpora=CORPORA))
            with self.assertRaises(ValueError):context_features(path,'2017-01',groups)
            with self.assertRaises(ValueError):context_features(path,'2017-01',groups,corpora=('x','x'))


class ArchiveTests(unittest.TestCase):
    def payload(self):
        stream=BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:archive.writestr('utterances.jsonl','{}\n')
        return stream.getvalue()

    def run_acquire(self,root,body,size=None,free=100*2**30):
        with patch('reddit_sna.data.confirmation.ARCHIVES',{'Fixture':('folder/',len(body) if size is None else size)}), \
             patch('reddit_sna.data.confirmation.CORPORA',('Fixture',)), \
             patch('reddit_sna.data.confirmation.urlopen',side_effect=lambda *a,**k:BytesIO(body)), \
             patch('reddit_sna.data.confirmation.shutil.disk_usage',return_value=SimpleNamespace(free=free)):
            return acquire(root,minimum_free_gib=1)

    def test_download_crc_hash_replay_and_changed_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);body=self.payload()
            result=self.run_acquire(root,body)
            self.assertEqual(result[0]['crc'],'passed')
            self.assertEqual(result[0]['sha256'],digest_file(root/'Fixture.corpus.zip'))
            self.assertEqual(result,self.run_acquire(root,body))
            (root/'Fixture.corpus.zip').write_bytes(body+b'changed')
            with self.assertRaisesRegex(ValueError,'changed'):self.run_acquire(root,body)

    def test_partial_size_crc_and_disk_failures_are_preserved(self):
        for mode in ('short','large','crc','disk'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);body=self.payload()
                if mode=='crc':body=body.replace(b'{}\n',b'bad')
                size=len(body)+(1 if mode=='short' else -1 if mode=='large' else 0)
                with self.assertRaises((ValueError,RuntimeError,zipfile.BadZipFile)):
                    self.run_acquire(root,body,size,free=0 if mode=='disk' else 100*2**30)
                self.assertFalse((root/'Fixture.corpus.zip').exists())
                if mode!='disk':
                    self.assertTrue((root/'Fixture.corpus.zip.partial').exists())
                    with self.assertRaises(FileExistsError):self.run_acquire(root,body,size)

    def test_fixed_allowlist_and_missing_file_fail_explicitly(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):declared_paths(temporary,('../escape',))
            with self.assertRaisesRegex(ValueError,'Missing'):declared_paths(temporary,CORPORA)

    def test_interrupted_stream_preserves_partial_and_requires_manual_recovery(self):
        class Interrupted(BytesIO):
            def read(self, size=-1):
                if self.tell():raise OSError('Simulated interrupted transport')
                return super().read(8)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);body=self.payload()
            with patch('reddit_sna.data.confirmation.ARCHIVES',{'Fixture':('folder/',len(body))}), \
                 patch('reddit_sna.data.confirmation.CORPORA',('Fixture',)), \
                 patch('reddit_sna.data.confirmation.urlopen',side_effect=lambda *a,**k:Interrupted(body)), \
                 patch('reddit_sna.data.confirmation.shutil.disk_usage',return_value=SimpleNamespace(free=100*2**30)):
                with self.assertRaisesRegex(OSError,'interrupted'):acquire(root,1)
            self.assertEqual((root/'Fixture.corpus.zip.partial').read_bytes(),body[:8])
            self.assertFalse((root/'Fixture.corpus.zip').exists())
            with self.assertRaises(FileExistsError):self.run_acquire(root,body)


if __name__=='__main__':unittest.main()
