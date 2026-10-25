"""Synthetic end-to-end study, freeze gate, provenance and resource stops."""

import json
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import zipfile

from reddit_sna.data.archive import CORPORA, digest_file
from reddit_sna.data.normalize import month_boundary
from reddit_sna.data.study import normalize_study
from reddit_sna.data.study_extension import extend_study
from reddit_sna.evaluation.temporal_protocol import load_temporal_protocol, months
from reddit_sna.pipelines.study_preparation import normalize_phase, prepare_month, seal, verified
from reddit_sna.pipelines.study_resources import monitored
from reddit_sna.pipelines.study_samples import build_study_samples, read_csv
from reddit_sna.pipelines.temporal_study import _attempt, _complete, _freeze, run_temporal_study
from reddit_sna.reporting.temporal_study import read_study

PROJECT=Path(__file__).parents[2]
PROTOCOL=PROJECT/'configs/temporal_study.toml'


def archives(root, end='2018-10'):
    """Tiny synthetic corpus; it is never evidence of Reddit model performance."""
    root.mkdir()
    for index,corpus in enumerate(sorted(CORPORA)):
        records=[]
        for month in months('2015-01',end):
            tag=month.replace('-','')
            post=f'p{index}_{tag}'
            records.append(dict(id='t3_'+post,root=post,reply_to=None,user='Alice' if index==0 else f'isolate{index}',
                timestamp=month_boundary(month),text='private body omitted'))
            if index==0:
                records.extend([
                    dict(id='t1_c'+tag+'a',root=post,reply_to='t3_'+post,user='Bob',timestamp=month_boundary(month)+86400),
                    dict(id='t1_c'+tag+'b',root=post,reply_to='t1_c'+tag+'a',user='Alice',timestamp=month_boundary(month)+2*86400)])
        if index==0:
            base=month_boundary('2015-01')
            records.extend([
                dict(id='t1_self',root='p0_201501',reply_to='t3_p0_201501',user='Alice',timestamp=base+3*86400),
                dict(id='t1_deleted',root='p0_201501',reply_to='t3_p0_201501',user='[deleted]',timestamp=base+4*86400),
                dict(id='t1_missing',root='p0_201501',reply_to='t1_absent',user='Dave',timestamp=base+5*86400),
                dict(id='t3_futureparent',root='futureparent',reply_to=None,user='Frank',timestamp=base+20*86400),
                dict(id='t1_futurechild',root='futureparent',reply_to='t3_futureparent',user='Eve',timestamp=base+10*86400)])
        with zipfile.ZipFile(root/f'{corpus}.corpus.zip','w') as archive:
            archive.writestr('utterances.jsonl','\n'.join(json.dumps(r) for r in records)+'\n')


class PreparationIntegrationTests(unittest.TestCase):
    def test_stable_cross_cutoff_identity_and_no_raw_author_text_persistence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);raw=root/'raw';archives(raw,'2015-04')
            paths=sorted(raw.glob('*.zip'))
            first=root/'first.sqlite';second=root/'second.sqlite'
            normalize_study(paths,first,'2015-02',progress=lambda *a,**kw:None)
            normalize_study(paths,second,'2015-04',progress=lambda *a,**kw:None)
            source_hash=digest_file(first)
            extended=root/'extended.sqlite'
            extend_study(paths,first,extended,'2015-04',progress=lambda *a,**kw:None)
            with closing(sqlite3.connect(first)) as left,closing(sqlite3.connect(second)) as right:
                before=left.execute('SELECT * FROM records ORDER BY id').fetchall()
                after=right.execute("SELECT * FROM records WHERE month<'2015-02' ORDER BY id").fetchall()
                self.assertEqual(before,after)
                dump='\n'.join(left.iterdump())
                self.assertNotIn('private body',dump)
                self.assertNotIn('Alice',dump)
                with closing(sqlite3.connect(extended)) as actual:
                    self.assertEqual(actual.execute('SELECT * FROM records ORDER BY id').fetchall(),
                                     right.execute('SELECT * FROM records ORDER BY id').fetchall())
            self.assertEqual(digest_file(first),source_hash)
            with self.assertRaises(FileExistsError):normalize_study(paths,first,'2015-02')

    def test_graph_losses_censoring_and_complete_sample_pipeline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);raw=root/'raw';archives(raw,'2015-03')
            store=root/'store';normalize_phase(raw,store,'2015-03')
            directories={}
            for month in ('2015-01','2015-02'):
                destination=root/month
                prepare_month(store/'normalized.sqlite',destination,month)
                directories[month]=destination
            graph=json.loads((directories['2015-01']/'snapshots.json').read_text())['months'][0]
            self.assertEqual(graph['reply_events'],2)
            self.assertEqual(graph['reply_endpoints'],2)
            self.assertGreater(graph['isolates'],0)
            self.assertEqual(graph['missing_parent'],1)
            self.assertEqual(graph['parent_after_child'],1)
            output=root/'samples'
            build_study_samples(store/'normalized.sqlite',directories,output,'synthetic-fixed-reference')
            verified(output)
            samples=read_csv(output/'samples.csv')
            self.assertEqual(len(samples),1)
            self.assertEqual(samples[0]['label'],'stable')
            labels=read_csv(output/'labels.csv')
            self.assertEqual(labels[-1]['reason'],'final_snapshot_censored')
            audit=json.loads((output/'label_audit.json').read_text())
            self.assertEqual(audit['human_review'],'pending')

    def test_hash_tampering_and_partial_attempt_preservation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);stage=root/'stage';stage.mkdir()
            payload=stage/'payload.csv';payload.write_text('value\n1\n')
            seal(stage,dict(status='complete'))
            verified(stage)
            payload.write_text('value\n2\n')
            with self.assertRaises(ValueError):verified(stage)
            attempt=_attempt(root,'partial');attempt.mkdir();(attempt/'progress.txt').write_text('retained')
            self.assertIsNone(_complete(root,'partial'))
            self.assertNotEqual(_attempt(root,'partial'),attempt)
            self.assertEqual((attempt/'progress.txt').read_text(),'retained')

    def test_verified_cache_matches_uncached_extended_features_and_targets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);raw=root/'raw';archives(raw,'2015-04')
            store=root/'store';normalize_phase(raw,store,'2015-04')
            directories={}
            for month in ('2015-01','2015-02','2015-03'):
                prepare_month(store/'normalized.sqlite',root/month,month)
                directories[month]=root/month
            past=root/'past'
            build_study_samples(store/'normalized.sqlite',{m:p for m,p in directories.items() if m<'2015-03'},past,'cache-fixture')
            full,cached=root/'full',root/'cached'
            build_study_samples(store/'normalized.sqlite',directories,full,'cache-fixture')
            build_study_samples(store/'normalized.sqlite',directories,cached,'cache-fixture',cache=past)
            for name in ('features.csv','samples.csv','labels.csv','tracking.csv','inclusion_pairs.csv'):
                self.assertEqual((full/name).read_bytes(),(cached/name).read_bytes(),name)
            self.assertEqual(verified(cached)['cached_feature_manifest_sha256'],digest_file(past/'complete.json'))
            with (past/'features.csv').open('a') as stream:stream.write('\nchanged')
            with self.assertRaises(ValueError):
                build_study_samples(store/'normalized.sqlite',directories,root/'bad-cache','cache-fixture',cache=past)

    def test_resource_worker_failure_limit_and_journal_preservation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            protocol=load_temporal_protocol(PROTOCOL)
            with self.assertRaises(RuntimeError):
                monitored([sys.executable,'-c','raise SystemExit(7)'],root,'failure',protocol)
            report=json.loads((root/'resources/failure.json').read_text())
            self.assertEqual(report['exit_code'],7)
            self.assertEqual(report['status'],'failed')
            with self.assertRaises(FileExistsError):
                monitored([sys.executable,'-c','pass'],root,'failure',protocol)
            with self.assertRaises(RuntimeError):
                monitored([sys.executable,'-c','import time; time.sleep(30)'],root,'limit',dict(protocol,memory_budget_gib=0))
            self.assertEqual(json.loads((root/'resources/limit.json').read_text())['status'],'resource_exceeded')


class FullSyntheticStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory()
        cls.base=Path(cls.temporary.name)
        cls.raw=cls.base/'raw';archives(cls.raw)
        cls.artifacts=cls.base/'artifacts'
        cls.study_root=cls.artifacts/'synthetic-study'
        # This negative control occurs before any test-period preparation.
        try:
            run_temporal_study(PROTOCOL,cls.raw,cls.study_root,'evaluate',cls.artifacts)
        except FileNotFoundError:
            cls.blocked_before_freeze=True
        else:
            cls.blocked_before_freeze=False
        for stage in ('normalize-development','develop','select','evaluate','report'):
            run_temporal_study(PROTOCOL,cls.raw,cls.study_root,stage,cls.artifacts)

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def test_end_to_end_freeze_matched_models_report_and_honest_scope(self):
        self.assertTrue(self.blocked_before_freeze)
        data=read_study(self.study_root)
        self.assertEqual(data['evaluation']['superiority'],'not_demonstrated')
        self.assertFalse(data['evaluation']['unseen'])
        self.assertEqual(data['label_audit']['human_review'],'pending')
        self.assertEqual(data['selection']['latest_training_label'],'2017-12')
        self.assertEqual(set(data['selection']['baselines']),
            {'B1_majority','B1_persistence','flat_lr_dynamic','hier_hgb_static','hier_hgb_dynamic'})
        self.assertEqual(len(data['selection']['models']),7)
        self.assertEqual(len(data['evaluation']['per_month'][data['evaluation']['proposed']]),9)
        report=_complete(self.study_root,'report-midterm-v3')
        self.assertEqual(len(list(report.glob('*.png'))),7)
        self.assertEqual(len(data['graph_scale']),45)
        self.assertEqual(data['quotient']['month'],'2015-01')
        text=(report/'MIDTERM_REPORT.md').read_text(encoding='utf-8')
        for heading in ('research questions','Network construction','Labels: definition',
                        'five baselines','Rare classes','Midterm requirement','References'):
            self.assertIn(heading,text)
        self.assertNotIn('Dự báo',text)
        from reddit_sna.reporting.temporal_study import study_diagnostics
        diagnostic=study_diagnostics(data)
        self.assertEqual(diagnostic['strongest_reference'],data['evaluation']['strongest_realized_baseline'])
        self.assertIn('retrospective',diagnostic['analysis'])

    def test_compact_projection_preserves_scores_and_rejects_hidden_baseline(self):
        from unittest.mock import patch
        from reddit_sna.reporting.temporal_study import read_compact_study
        from copy import deepcopy
        original=read_study(self.study_root)
        compact=read_compact_study(self.study_root)
        self.assertEqual(compact['evaluation']['intervals'],original['evaluation']['intervals'])
        self.assertEqual(compact['evaluation']['mean_macro_f1'],original['evaluation']['mean_macro_f1'])
        self.assertEqual(len(compact['selection']['models']),7)
        for field in ('strongest_realized_baseline','validation_selected_champion','proposed'):
            invalid=deepcopy(original)
            invalid['evaluation'][field]='omitted_stronger_model'
            with patch('reddit_sna.reporting.temporal_study.read_study',return_value=invalid):
                with self.assertRaises(ValueError):read_compact_study(self.study_root)

    def test_freeze_rejects_changed_model_protocol_and_source_record(self):
        selection,development=_freeze(self.study_root)
        model=next(selection.glob('*.joblib'))
        for path in (model,development/'features.csv',self.study_root/'protocol.json',self.study_root/'freeze.json'):
            original=path.read_bytes()
            try:
                if path.name=='freeze.json':
                    value=json.loads(original);value['critical_source_hashes']['data/study.py']='changed'
                    path.write_text(json.dumps(value))
                else:path.write_bytes(original+b'\nchanged')
                with self.assertRaises((ValueError,json.JSONDecodeError)):_freeze(self.study_root)
            finally:path.write_bytes(original)
        _freeze(self.study_root)

    def test_completed_months_are_reused_and_unsafe_destination_refused(self):
        month=_complete(self.study_root,'month-2015-01')
        before=digest_file(month/'complete.json')
        from reddit_sna.pipelines.temporal_study import _prepare
        store=_complete(self.study_root,'development-store')
        _prepare(self.study_root,store/'normalized.sqlite','2015-01','2015-02')
        self.assertEqual(before,digest_file(month/'complete.json'))
        with self.assertRaises(ValueError):
            run_temporal_study(PROTOCOL,self.raw,self.base/'outside','develop',self.artifacts)


if __name__=='__main__':unittest.main()
