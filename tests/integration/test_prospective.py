"""Real graph, target, fit and append stages on explicitly synthetic archives."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from sklearn.metrics import f1_score

from reddit_sna.data.archive import digest_file
from reddit_sna.data.normalize import month_boundary
from reddit_sna.evaluation.temporal_protocol import EVENTS, months
from reddit_sna.pipelines.prospective import CANDIDATE, CORPORA, declare, frozen, load_protocol, panel_path, work
from reddit_sna.pipelines.study_preparation import verified
from reddit_sna.pipelines.study_resources import json_write
from reddit_sna.pipelines.study_samples import read_csv
from reddit_sna.pipelines.temporal_study import _complete
from reddit_sna.reporting.prospective import read_prospective, render_prospective

PROJECT=Path(__file__).parents[2]
PROTOCOL=PROJECT/'configs/prospective.toml'


class ProspectiveIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)
        protocol,definitions,model_path=load_protocol(PROTOCOL)
        # The public loader refuses these fixture byte sizes. Only the internal
        # worker is supplied this explicitly synthetic protocol for integration.
        cls.protocol=deepcopy(protocol)
        cls.definitions=definitions
        raw=cls.root/'fixture-input'
        raw.mkdir()
        for index,name in enumerate(CORPORA):
            records=[]
            for month in months('2015-01','2018-10'):
                tag=month.replace('-','')
                post=f'p{index}_{tag}'
                comment=f'c{index}_{tag}'
                records.extend([
                    dict(id='t3_'+post,root=post,reply_to=None,user=f'a{index}',timestamp=month_boundary(month),text='synthetic'),
                    dict(id='t1_'+comment,root=post,reply_to='t3_'+post,user=f'b{index}',timestamp=month_boundary(month)+86400,text='synthetic'),
                    dict(id='t1_'+comment+'x',root=post,reply_to='t1_'+comment,user=f'a{index}',timestamp=month_boundary(month)+2*86400,text='synthetic')])
            target=raw/(name+'.corpus.zip')
            with zipfile.ZipFile(target,'w') as archive:
                archive.writestr('utterances.jsonl','\n'.join(json.dumps(r) for r in records)+'\n')
            cls.protocol['archives'][name]['bytes']=target.stat().st_size
            json_write(raw/(name+'.json'),dict(url=protocol['archives'][name]['url'],sha256=digest_file(target)))
        cls.study=cls.root/'study'
        cls.study.mkdir()
        declare(cls.study,cls.protocol,definitions,PROTOCOL,model_path)
        raw.rename(cls.study/'raw')
        json_write(cls.study/'acquisition.json',dict(completed_utc=datetime.now(timezone.utc).isoformat(),archives=[],
            declaration_sha256=digest_file(cls.study/'declaration.json')))
        work(cls.study,cls.protocol,definitions,'develop')
        cls.development=_complete(cls.study,'development-samples')
        cls.prefix=read_csv(cls.development/'samples.csv')
        cls.no_final_before_fit=not (cls.study/'stages/month-2018-01').exists()
        work(cls.study,cls.protocol,definitions,'fit')
        cls.freeze_before_final=not (cls.study/'stages/month-2018-01').exists()
        work(cls.study,cls.protocol,definitions,'evaluate')
        work(cls.study,cls.protocol,definitions,'review')
        cls.data=read_prospective(cls.study)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_final_targets_follow_freeze_and_prefix_is_unchanged(self):
        self.assertTrue(self.no_final_before_fit)
        self.assertTrue(self.freeze_before_final)
        full=read_csv(_complete(self.study,'evaluation-samples')/'samples.csv')
        self.assertEqual(self.prefix,[r for r in full if r['label_month']<'2018-01'])
        frozen(self.study)
        self.assertEqual(self.data['selection']['latest_training_label'],'2017-12')

    def test_all_nine_methods_have_same_final_keys_and_fixed_six_scores(self):
        evaluation=self.data['evaluation']
        self.assertEqual(len(evaluation['mean_macro_f1']),9)
        rows=self.data['predictions']
        primary=[r for r in rows if r['model']==CANDIDATE and int(r['seed'])==42]
        oracle=f1_score([r['y_true'] for r in primary],[r['y_pred'] for r in primary],
                        labels=list(EVENTS),average='macro',zero_division=0)
        self.assertAlmostEqual(oracle,evaluation['mean_macro_f1'][CANDIDATE])
        self.assertAlmostEqual(oracle,1/6)
        self.assertEqual(evaluation['metrics'][f'{CANDIDATE}:42']['per_class']['grow']['support'],0)

    def test_source_protocol_and_model_drift_are_rejected(self):
        protocol=self.study/'protocol.json'
        original=protocol.read_bytes()
        try:
            protocol.write_bytes(original+b' ')
            with self.assertRaises(ValueError):frozen(self.study)
        finally:protocol.write_bytes(original)
        selection=_complete(self.study,'selection')
        model=selection/(CANDIDATE+'-42.joblib')
        original=model.read_bytes()
        try:
            model.write_bytes(original+b'corrupt')
            with self.assertRaises(ValueError):frozen(self.study)
        finally:model.write_bytes(original)

    def test_worker_refuses_a_config_changed_between_parent_and_child(self):
        changed=deepcopy(self.definitions)
        changed[CANDIDATE]['settings']['C']=.1
        with self.assertRaisesRegex(ValueError,'pre-acquisition'):
            work(self.study,self.protocol,changed,'fit')

    def test_primary_remains_declared_after_all_outcomes(self):
        self.assertEqual(self.data['selection']['proposed'],CANDIDATE)
        self.assertEqual(self.data['declaration']['primary_fixed'],CANDIDATE)
        self.assertEqual(self.data['declaration']['definitions'],self.definitions)
        text=render_prospective(self.data)
        self.assertIn('no model is replaced',text)
        self.assertIn('not independent',text)

    def test_panel_does_not_complete_human_assessment(self):
        panel=panel_path(self.study)
        verified(panel)
        manifest=json.loads((panel/'manifest.json').read_text())
        self.assertEqual(manifest['human_review'],'pending')
        self.assertFalse(any(r['label'] for r in read_csv(panel/'reviewer/assessment_1.csv')))


if __name__=='__main__':unittest.main()
