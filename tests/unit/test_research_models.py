"""Actual model fits verify capacity controls, persistence and class fallbacks."""

import copy
from pathlib import Path
import tempfile
import unittest

from threadpoolctl import threadpool_limits

from reddit_sna.evaluation.research_protocol import FULL, HGB, VARIANTS, load_protocol
from reddit_sna.models.research import fit_variant, predict_variant


class ResearchModelsTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{**{f: float(i % 3) for f in FULL}, 'label': 'grow' if i % 2 else 'stable', 'past_event':''}
                     for i in range(30)]

    def test_b5_and_a1_share_real_fit_settings_and_predictions(self):
        with threadpool_limits(limits=1):
            b5=fit_variant('B5_matched_boosting',self.rows,42)
            a1=fit_variant('A1_no_context',self.rows,42)
            proposed=fit_variant('HeTCo_v0',self.rows,42)
            for fitted in (b5,a1,proposed):
                for name,value in HGB.items():self.assertEqual(fitted['model'].get_params()[name],value)
            self.assertEqual(predict_variant(b5,self.rows),predict_variant(a1,self.rows))
            self.assertGreater(len(proposed['fields']),len(b5['fields']))

    def test_single_class_is_explicit_fallback_for_all_variants(self):
        rows=copy.deepcopy(self.rows)
        for r in rows:r['label']='grow'
        for name in VARIANTS:
            fitted=fit_variant(name,rows,42)
            prediction,fallback=predict_variant(fitted,rows[:2])
            self.assertTrue(fitted['single_class_fallback'])
            self.assertEqual(prediction,['grow','grow'])
            self.assertEqual(fallback,[1,1])

    def test_persistence_uses_known_event_else_training_majority(self):
        fitted=fit_variant('B1_persistence',self.rows,42)
        test=[{**self.rows[0],'past_event':'split'},{**self.rows[1],'past_event':''}]
        prediction,fallback=predict_variant(fitted,test)
        self.assertEqual(prediction[0],'split');self.assertIn(prediction[1],('grow','stable'))
        self.assertEqual(fallback,[0,1])

    def test_protocol_rejects_unknown_fields_retuning_and_boolean_seeds(self):
        source=(Path(__file__).resolve().parents[2]/'configs/midterm.toml').read_text()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'config.toml'
            for text in (source.replace('max_iter = 100','max_iter = 101'),
                         source.replace('seeds = [42, 43, 44]','seeds = [true, 43, 44]'),
                         source.replace('schema_version = 1','unknown = 3\nschema_version = 1')):
                path.write_text(text,encoding='utf-8')
                with self.assertRaises(ValueError):load_protocol(path)

    def test_nonfinite_features_are_refused(self):
        self.rows[0]['size']=float('nan')
        with self.assertRaisesRegex(ValueError,'finite'):
            fit_variant('HeTCo_v0',self.rows,42)
