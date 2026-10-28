"""Real LR fits and sealed synthetic cohorts exercise the complete worker."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from threadpoolctl import threadpool_limits

from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.components import FULL, SETTINGS, definitions, load_protocol
from reddit_sna.evaluation.research import KEY
from reddit_sna.evaluation.temporal_protocol import FIELDS, PRIMARY
from reddit_sna.models.activity_forecast import fit_activity_model, predict_activity_model
from reddit_sna.pipelines.components import load_cohort, work
from reddit_sna.pipelines.study_preparation import seal, verified
from reddit_sna.pipelines.study_resources import json_write
from reddit_sna.pipelines.study_samples import read_csv, write_csv
from reddit_sna.reporting.components import read_components, render_components
from tests.unit.test_components import samples


def make_source(root,protocol,reference):
    """Construct a sealed, explicitly synthetic historical run with genuine fits."""
    root.mkdir()
    paths = {}
    for stage in ('development-samples','evaluation-samples','selection','evaluation'):
        paths[stage] = root/'stages'/stage/'attempt-001'
        paths[stage].mkdir(parents=True)
    rows = samples(reference=reference)
    dev = [r for r in rows if r['label_month']<'2018-01']
    final = [r for r in rows if r['label_month']>='2018-01']
    for stage,subset in (('development-samples',dev),('evaluation-samples',rows)):
        folder = paths[stage]
        write_csv(folder/'samples.csv',subset)
        write_csv(folder/'labels.csv',[dict(r,eligible=1,reason='synthetic_fixture') for r in subset])
        write_csv(folder/'inclusion_pairs.csv',[],fields=['feature_month','source_community_id','accepted'])
        json_write(folder/'label_audit.json',dict(status='automated_rule_consistency_verified',
                   fixture='Synthetic IO fixture, not actual Reddit or social validation'))
        review = folder/'review/reviewer'
        review.mkdir(parents=True)
        json_write(review/'cases.json',[dict(case_id='synthetic-1',scope='synthetic')])
        write_csv(review/'annotations.csv',[dict(case_id='synthetic-1',reviewer=role,human_label='',rationale='')
                  for role in ('reviewer_a','reviewer_b')])
        seal(folder,dict(status='complete',stage=stage))
    primary = dict(kind='activity',**definitions()[FULL])
    json_write(paths['selection']/'selection.json',dict(definitions={PRIMARY:primary}))
    seal(paths['selection'],dict(status='complete',stage='selection'))
    predictions = []
    with threadpool_limits(limits=1):
        for name,fields in ((PRIMARY,FIELDS['dynamic']),('A_no_dynamics_matched',FIELDS['static'])):
            for seed in protocol['seeds']:
                fitted = fit_activity_model(dev,fields,SETTINGS,True,seed)
                guesses,probabilities,flags = predict_activity_model(fitted,final)
                for row,guess,probability,flag in zip(final,guesses,probabilities,flags):
                    record = {k:row[k] for k in (*KEY,'size')}
                    record.update(model=name,seed=seed,y_true=row['label'],y_pred=guess,fallback=flag,
                                  probabilities=json.dumps(probability))
                    predictions.append(record)
    write_csv(paths['evaluation']/'predictions.csv',predictions)
    seal(paths['evaluation'],dict(status='complete',stage='evaluation',
        selection_manifest_sha256=digest_file(paths['selection']/'complete.json'),
        sample_manifest_sha256=digest_file(paths['evaluation-samples']/'complete.json')))
    json_write(root/'protocol.json',protocol)
    json_write(root/'freeze.json',dict(selection=str(paths['selection'].relative_to(root)),
        selection_manifest_sha256=digest_file(paths['selection']/'complete.json'),
        development_samples=str(paths['development-samples'].relative_to(root)),
        development_manifest_sha256=digest_file(paths['development-samples']/'complete.json'),
        development_samples_sha256=digest_file(paths['development-samples']/'samples.csv'),
        protocol_sha256=digest_file(root/'protocol.json')))


class ComponentIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.protocol_path = Path(__file__).parents[2]/'configs/components.toml'
        cls.protocol = load_protocol(cls.protocol_path)
        cls.original,cls.external = cls.root/'original',cls.root/'external'
        make_source(cls.original,cls.protocol,'synthetic-original')
        make_source(cls.external,cls.protocol,'synthetic-external')
        cls.output = cls.root/'output'
        cls.output.mkdir()
        work(cls.protocol_path,cls.original,cls.external,cls.output)
        seal(cls.output,dict(status='complete',stage='synthetic-component-integration'))
        cls.results = read_components(cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_all_controls_and_temporal_fit_boundaries(self):
        for cohort in ('original','external'):
            folder = self.output/cohort
            fits = json.loads((folder/'fits.json').read_text())
            self.assertEqual(len(fits),8*3*7)
            self.assertTrue(all(r['latest_train_label']<r['origin'] for r in fits))
            self.assertEqual(set(self.results[cohort]['final']['mean_macro_f1']),set(definitions()))
            self.assertEqual(self.results[cohort]['final']['samples'],54)
            checks = json.loads((folder/'reproduction.json').read_text())
            self.assertTrue(all(r['mismatches']==0 for r in checks.values()))

    def test_prepared_forms_and_automation_never_become_human_review(self):
        for cohort in ('original','external'):
            readiness = json.loads((self.output/cohort/'review_readiness.json').read_text())
            self.assertEqual(readiness['human_review'],'pending')
            self.assertEqual(readiness['actual_human_submissions'],0)
            self.assertIsNone(readiness['human_agreement'])
            self.assertIn('automated',readiness['assessment_source'])
            forms = read_csv(self.output/cohort/'review_forms.csv')
            self.assertTrue(all(not r['human_label'] and not r['rationale'] for r in forms))
            self.assertFalse(any(r['reviewer'] in ('Tam','Thanh','Tâm') for r in forms))

    def test_exposed_data_never_certifies_a_fresh_evaluation(self):
        status = json.loads((self.output/'new_data_eligibility.json').read_text())
        self.assertFalse(status['new_untouched_cohort_verified'])
        self.assertFalse(status['new_cohort_evaluated'])
        self.assertTrue(all(r['exposed'] for r in status['existing_sources'].values()))
        self.assertEqual(status['status'],'prospective_evaluation_pending')

    def test_corrupt_payload_is_rejected_and_report_preserves_negative_scope(self):
        text = render_components(self.results)
        self.assertIn('A2_flat_matched',text)
        self.assertIn('not completed human assessment',text)
        self.assertIn('already exposed',text)
        path = self.output/'original/review_forms.csv'
        original = path.read_bytes()
        try:
            path.write_bytes(original+b'corruption')
            with self.assertRaises(ValueError):read_components(self.output)
        finally:
            path.write_bytes(original)

    def test_corrupt_source_manifest_is_rejected_without_writing_output(self):
        path = self.original/'stages/development-samples/attempt-001/samples.csv'
        original = path.read_bytes()
        try:
            path.write_bytes(original+b'corruption')
            with self.assertRaises(ValueError):load_cohort(self.original,self.protocol)
        finally:
            path.write_bytes(original)

    def test_real_reviewer_subdirectory_is_a_required_preflight_input(self):
        source = load_cohort(self.original,self.protocol)
        self.assertTrue((source['stages']['development-samples']/'review/reviewer/cases.json').is_file())


if __name__ == '__main__':
    unittest.main()
