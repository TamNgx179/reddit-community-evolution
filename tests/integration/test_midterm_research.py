"""Actual archive/SQLite -> fixed-reference proposed experiment, without mocks."""

from dataclasses import replace
import contextlib
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from contextlib import closing
import sqlite3
from unittest.mock import patch

from reddit_sna.config import load_config
from reddit_sna.pipelines.preparation import run_preparation
from reddit_sna.pipelines.forecast import run_forecast
from reddit_sna.pipelines.research import run_research
from reddit_sna.reporting.research import read_research, build_figures
from tests.corpus_support import archive, record


class MidtermResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='midterm-research-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name);(cls.root/'data/raw').mkdir(parents=True)
        (cls.root/'configs').mkdir();cls.artifacts=cls.root/'artifacts'
        cls.config=cls.root/'configs/core.toml'
        cls.config.write_text('schema_version=1\npipeline="core"\nproject_root=".."\nseed=42\n'
            '[input]\nkind="reddit"\npath="../data/raw"\n[output]\nroot="../artifacts"\nrun_id="prepared"\n',encoding='utf-8')
        cls.protocol=cls.root/'configs/midterm.toml'
        shutil.copy2(Path(__file__).resolve().parents[2]/'configs/midterm.toml',cls.protocol)
        rows=[]
        for month in range(1,13):
            day=f'2015-{month:02d}-02'
            # One community changes size, the other remains stable. Distinct
            # disconnected reply stars give known temporal variation naturally.
            for group in ('a','b'):
                root=f'p-{month}-{group}'
                rows.append(record(root,f'synthetic-{group}-0',root=root,day=day))
                for i in range(1,3 if group=='a' and month%2 else 2):
                    rows.append(record(f'c-{month}-{group}-{i}',f'synthetic-{group}-{i}',
                                       root=root,parent=root,day=day))
        archive(cls.root/'data/raw/moderatepolitics.corpus.zip',rows)
        with contextlib.redirect_stdout(io.StringIO()):
            cls.preparation=run_preparation(load_config(cls.config),start='2015-01',end='2016-01',corpora=('moderatepolitics',))
        cls.forecast=run_forecast(cls.preparation,cls.preparation,cls.artifacts,cls.artifacts/'core/forecast',
                                  '2015-10',tracker='ged',history=True)
        cls.output=run_research(cls.protocol,cls.preparation,cls.forecast,cls.artifacts,'test-study')
        cls.delivery=read_research(cls.output)

    def copy_run(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        target=Path(tmp.name)/'run';shutil.copytree(self.output,target);return target

    @staticmethod
    def reseal(run,name):
        path=run/'manifest.json';m=json.loads(path.read_text())
        m['artifact_hashes'][name]=sha256((run/name).read_bytes()).hexdigest()
        path.write_text(json.dumps(m),encoding='utf-8')

    def test_real_run_has_matched_models_and_protocol_before_fit(self):
        d=self.delivery;m=d['manifest']
        self.assertEqual(m['status'],'complete')
        self.assertLessEqual(m['protocol_frozen_at'],m['first_fit_at'])
        self.assertEqual(len(d['fits']),7*9*3)
        self.assertTrue(any(not f['single_class_fallback'] for f in d['fits']))
        self.assertFalse(m['unseen']);self.assertEqual(m['human_annotation'],'pending')
        self.assertIn('status',m['git'])
        self.assertTrue(m['source_archive'])
        self.assertTrue((self.output/'provenance/source/reddit_sna/features/context.py').is_file())
        self.assertEqual(d['evaluation']['uncertainty']['status'],'exploratory_only')
        for r in d['evaluation']['means']:
            if r['model']=='A1_no_context':self.assertEqual(r['delta_vs_B5'],0)

    def test_reused_output_and_outside_sources_are_refused(self):
        before=(self.output/'manifest.json').read_bytes()
        with self.assertRaises(ValueError):
            run_research(self.protocol,self.preparation,self.forecast,self.artifacts,'test-study')
        self.assertEqual((self.output/'manifest.json').read_bytes(),before)
        with self.assertRaises(ValueError):
            run_research(self.protocol,self.root,self.forecast,self.artifacts,'outside')
        with self.assertRaises(ValueError):
            run_research(self.protocol,self.preparation,self.forecast,self.artifacts,'../unsafe')

    def test_missing_prediction_is_refused_even_after_resealing(self):
        run=self.copy_run();path=run/'predictions.csv'
        lines=path.read_text().splitlines();path.write_text('\n'.join(lines[:-1])+'\n',encoding='utf-8')
        self.reseal(run,'predictions.csv')
        with self.assertRaises(ValueError):read_research(run)

    def test_resealed_false_metrics_and_fit_features_are_refused(self):
        for name in ('evaluation.json','fits.json'):
            with self.subTest(name=name):
                run=self.copy_run();p=run/name;data=json.loads(p.read_text())
                if name=='evaluation.json':data['means'][0]['mean_macro_f1_six']=.99999
                else:data[0]['features']=['size_t_plus_1']
                p.write_text(json.dumps(data),encoding='utf-8');self.reseal(run,name)
                with self.assertRaises(ValueError):read_research(run)

    def test_resealed_label_reference_and_unsealed_hash_corruption_refused(self):
        run=self.copy_run();p=run/'samples.csv';p.write_text(p.read_text().replace(self.delivery['manifest']['label_reference_id'],'wrong'),encoding='utf-8')
        self.reseal(run,'samples.csv')
        with self.assertRaises(ValueError):read_research(run)
        run=self.copy_run();(run/'predictions.csv').write_text('corrupt',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'hash'):read_research(run)

    def test_figure_families_are_drawn_from_verified_results(self):
        import matplotlib.pyplot as plt
        figures=build_figures(self.delivery)
        self.assertEqual(set(figures),{'population','comparison','ablations','monthly','confusion','context','uncertainty'})
        for fig in figures.values():self.assertTrue(fig.axes);plt.close(fig)

    def test_resealed_sqlite_identity_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifacts=Path(tmp)/'artifacts';preparation=artifacts/'core/preparation';forecast=artifacts/'core/forecast'
            shutil.copytree(self.preparation,preparation);shutil.copytree(self.forecast,forecast)
            with closing(sqlite3.connect(preparation/'normalized.sqlite')) as db,db:
                db.execute("UPDATE provenance SET value='different-cohort' WHERE key='identity_scope'")
            path=preparation/'manifest.json';m=json.loads(path.read_text())
            m['artifact_hashes']['normalized.sqlite']=sha256((preparation/'normalized.sqlite').read_bytes()).hexdigest()
            path.write_text(json.dumps(m),encoding='utf-8')
            fp=forecast/'manifest.json';fm=json.loads(fp.read_text())
            fm['source_manifests']={str(preparation):sha256(path.read_bytes()).hexdigest()}
            fp.write_text(json.dumps(fm),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'identity scope'):
                run_research(self.protocol,preparation,forecast,artifacts,'wrong-scope')
            self.assertFalse((artifacts/'research/wrong-scope').exists())

    def test_source_change_during_real_fits_records_failed_status(self):
        from reddit_sna.models.research import fit_variant
        with tempfile.TemporaryDirectory() as tmp:
            protocol=Path(tmp)/'protocol.toml';shutil.copy2(self.protocol,protocol)
            changed=False
            def mutate_after_actual_fit(*args,**kwargs):
                nonlocal changed
                fitted=fit_variant(*args,**kwargs)
                if not changed:
                    protocol.write_text(protocol.read_text()+'\n# concurrent edit\n',encoding='utf-8');changed=True
                return fitted
            # Fault injection wraps actual fitting, not a model/service mock.
            with patch('reddit_sna.pipelines.research.fit_variant',side_effect=mutate_after_actual_fit):
                with self.assertRaisesRegex(ValueError,'changed during execution'):
                    run_research(protocol,self.preparation,self.forecast,self.artifacts,'changed-source')
            m=json.loads((self.artifacts/'research/changed-source/manifest.json').read_text())
            self.assertEqual(m['status'],'failed')
