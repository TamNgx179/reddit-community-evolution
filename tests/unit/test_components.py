"""Synthetic negative controls for the finite component experiment."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from sklearn.metrics import f1_score
from threadpoolctl import threadpool_limits

from reddit_sna.contracts import shift_month
from reddit_sna.evaluation.components import FULL, GROUPS, SETTINGS, definitions, load_protocol, summarize, validate_samples
from reddit_sna.evaluation.temporal_protocol import EVENTS, FIELDS, months
from reddit_sna.models.activity_forecast import fit_activity_model, predict_activity_model
from reddit_sna.pipelines.components import load_cohort, run


def samples(start='2017-01', end='2018-10', reference='synthetic-components'):
    """All six events at each month with deterministic, finite covariates."""
    rows = []
    for month in months(start,end):
        for i,label in enumerate(EVENTS):
            row = {f:float(i+1) for f in FIELDS['dynamic']}
            row.update(reference_id=reference, label_reference_id=reference+'-labels',
                feature_month=shift_month(month,-1), label_month=month, community_id=f'c{i}',
                label=label, size=i+2)
            rows.append(row)
    return rows


def predictions(month_count=9):
    rows = samples('2018-01',shift_month('2018-01',month_count))
    output = []
    for model in definitions():
        for seed in (42,43,44):
            for row in rows:
                output.append(dict(row,model=model,seed=seed,y_true=row['label'],
                    y_pred=row['label'] if model==FULL else 'stable',fallback=0))
    return output


class ComponentTests(unittest.TestCase):
    def test_only_hierarchy_changes_in_A2(self):
        defs = definitions()
        self.assertEqual(len(defs),8)
        self.assertEqual(len(defs[FULL]['fields']),37)
        a,b = deepcopy(defs[FULL]),deepcopy(defs['A2_flat_matched'])
        self.assertTrue(a.pop('hierarchical'))
        self.assertFalse(b.pop('hierarchical'))
        self.assertEqual(a,b)
        self.assertEqual(a['settings'],SETTINGS)

    def test_deletions_partition_D_and_preserve_observation_flags(self):
        defs = definitions()
        removed = [f for group in GROUPS.values() for f in group]
        self.assertEqual(len(removed),len(set(removed)))
        self.assertEqual(set(removed),set(FIELDS['dynamic'])-set(FIELDS['static']))
        self.assertEqual(defs['A1_no_D']['fields'],list(FIELDS['static']))
        for group,fields in GROUPS.items():
            expected = [f for f in FIELDS['dynamic'] if f not in fields]
            self.assertEqual(defs['without_'+group]['fields'],expected)
            self.assertEqual(defs['without_'+group]['settings'],SETTINGS)
            if group != 'observation_flags':
                self.assertTrue(set(GROUPS['observation_flags']) <= set(expected))

    def test_samples_reject_duplicate_reference_future_and_nonfinite(self):
        rows = samples('2017-01','2017-03')
        validate_samples(rows)
        for mutation in ('duplicate','reference','future','nan'):
            bad = deepcopy(rows)
            if mutation=='duplicate': bad.append(bad[0])
            elif mutation=='reference': bad[0]['reference_id']='another'
            elif mutation=='future': bad[0]['feature_month']='2018-01'
            else: bad[0]['context_drift_js']=float('nan')
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                validate_samples(bad)

    def test_metrics_and_paired_intervals_against_independent_oracle(self):
        rows = predictions()
        result = summarize(rows,[42,43,44],list(definitions()),months('2018-01','2018-10'),draws=50)
        selected = [r for r in rows if r['model']=='A2_flat_matched' and r['seed']==42]
        oracle = f1_score([r['y_true'] for r in selected],[r['y_pred'] for r in selected],labels=list(EVENTS),average='macro',zero_division=0)
        self.assertAlmostEqual(result['mean_macro_f1']['A2_flat_matched'],oracle)
        self.assertEqual(result['mean_macro_f1'][FULL],1.)
        ci = result['full_minus_control']['A2_flat_matched']['ci95']
        self.assertAlmostEqual(ci['low'],1-oracle)
        self.assertAlmostEqual(ci['high'],1-oracle)
        self.assertEqual(result['per_seed']['A2_flat_matched']['42']['per_class']['stable']['support'],9)

    def test_too_few_blocks_returns_unavailable_not_fake_interval(self):
        result = summarize(predictions(6),[42,43,44],list(definitions()),months('2018-01','2018-07'),draws=20)
        self.assertEqual(result['uncertainty']['status'],'insufficient_temporal_blocks')
        self.assertTrue(all(v['ci95'] is None for v in result['full_minus_control'].values()))

    def test_prediction_inventory_rejects_missing_duplicate_and_changed_truth(self):
        for mutation in ('missing','duplicate','truth','reference','month','seed'):
            rows = predictions()
            if mutation=='missing': rows.pop()
            elif mutation=='duplicate': rows.append(deepcopy(rows[0]))
            elif mutation=='truth': rows[-1]['y_true']='stable'
            elif mutation=='reference': rows[-1]['label_reference_id']='other'
            elif mutation=='month': rows[-1]['label_month']='2019-01'
            else: rows[-1]['seed']=99
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                summarize(rows,[42,43,44],list(definitions()),months('2018-01','2018-10'),draws=5)

    def test_constant_training_has_documented_fallback_and_six_probabilities(self):
        rows = [r for r in samples('2017-01','2017-03') if r['label']=='dissolve']
        with threadpool_limits(limits=1):
            fitted = fit_activity_model(rows,FIELDS['dynamic'],SETTINGS,True,42)
            guesses, probabilities, flags = predict_activity_model(fitted,rows)
        self.assertEqual(guesses,['dissolve']*2)
        self.assertTrue(all(flags))
        self.assertEqual(np.asarray(probabilities).shape,(2,6))
        np.testing.assert_allclose(np.asarray(probabilities).sum(axis=1),1)

    def test_protocol_changes_and_reused_destinations_rejected(self):
        source = Path(__file__).parents[2]/'configs/components.toml'
        load_protocol(source)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'protocol.toml'
            path.write_text(source.read_text().replace('bootstrap_draws = 2000','bootstrap_draws = 1'))
            with self.assertRaises(ValueError):load_protocol(path)
            with self.assertRaises(FileExistsError):
                self._existing(source,Path(directory))

    @staticmethod
    def _existing(protocol,root):
        output = root/'exists'
        output.mkdir()
        return run(protocol,root/'a',root/'b',output,root)

    def test_source_requires_freeze_and_manifest(self):
        protocol = load_protocol(Path(__file__).parents[2]/'configs/components.toml')
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):load_cohort(Path(directory),protocol)


if __name__ == '__main__':
    unittest.main()
