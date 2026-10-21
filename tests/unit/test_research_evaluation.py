"""Independent expected metrics and paired-schedule refusal cases."""

import copy
from pathlib import Path
import unittest

from sklearn.metrics import f1_score

from reddit_sna.contracts import next_month
from reddit_sna.evaluation.research import analyze_predictions, block_intervals, matrix_score, score
from reddit_sna.evaluation.research_protocol import VARIANTS, load_protocol


def prediction_fixture():
    protocol=load_protocol(Path(__file__).resolve().parents[2]/'configs/midterm.toml')
    # Unit bootstrap uses fewer draws; production loader still requires 1000.
    protocol['bootstrap']['draws']=20
    rows=[]
    for window in ('main','rolling'):
        for month in protocol['rolling_months']:
            if window=='main' and month<protocol['test_start']:continue
            feature=f'2015-{int(month[-2:])-1:02d}'
            for name in VARIANTS:
                for seed in protocol['seeds']:
                    for i,label in enumerate(('grow','stable')):
                        rows.append(dict(window=window,model=name,seed=seed,reference_id='membership',
                            label_reference_id='fixed-label-reference',feature_month=feature,label_month=month,
                            community_id=f'c{i}',y_true=label,y_pred=label,fallback=0))
    return protocol,rows


class ResearchEvaluationTests(unittest.TestCase):
    def test_six_class_and_present_class_metrics_match_sklearn(self):
        rows=[dict(y_true='grow',y_pred='grow',fallback=0),dict(y_true='grow',y_pred='stable',fallback=1)]
        result=score(rows)
        self.assertAlmostEqual(result['macro_f1_six'],f1_score(['grow','grow'],['grow','stable'],
            labels=['stable','grow','shrink','merge','split','dissolve'],average='macro',zero_division=0))
        self.assertAlmostEqual(result['macro_f1_present'],2/3)
        self.assertEqual(result['per_class']['stable']['support'],0)
        self.assertEqual(result['fallback'],1)
        self.assertIsNone(matrix_score([[0]*6 for _ in range(6)])['macro_f1_present'])

    def test_identical_seed_repeats_have_zero_paired_intervals(self):
        protocol,rows=prediction_fixture()
        result=analyze_predictions(rows,protocol)
        self.assertEqual(result,analyze_predictions(rows,protocol))
        uncertainty=result['uncertainty']
        self.assertEqual(len(uncertainty['rolling_months']),6)
        self.assertEqual(uncertainty['main_holdout']['status'],'unavailable')
        for value in uncertainty['intervals'].values():self.assertEqual(value,dict(low=0,high=0))

    def test_missing_duplicate_and_mixed_reference_predictions_refused(self):
        protocol,rows=prediction_fixture()
        for changed in (rows[:-1],rows+[dict(rows[0])]):
            with self.assertRaises(ValueError):analyze_predictions(changed,protocol)
        changed=copy.deepcopy(rows);changed[-1]['reference_id']='other'
        with self.assertRaises(ValueError):analyze_predictions(changed,protocol)

    def test_inconsistent_truth_and_out_of_window_rows_refused(self):
        protocol,rows=prediction_fixture()
        changed=copy.deepcopy(rows);changed[-1]['y_true']='split'
        with self.assertRaisesRegex(ValueError,'Truth differs'):analyze_predictions(changed,protocol)
        changed=copy.deepcopy(rows);changed[0]['label_month']='2015-08'
        with self.assertRaises(ValueError):analyze_predictions(changed,protocol)

    def test_too_few_time_blocks_returns_reason(self):
        protocol,_=prediction_fixture();protocol['rolling_months']=protocol['rolling_months'][:3]
        self.assertEqual(block_intervals({},protocol),dict(status='unavailable',reason='insufficient_time_blocks'))
