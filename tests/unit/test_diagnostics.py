"""Known denominators, causal member summaries and paired uncertainty controls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from reddit_sna.evaluation.diagnostics import coverage_tables, forecast_tables, paired_tables, prediction_units
from reddit_sna.features.member_summary import MEAN_FIELDS, member_mean
from reddit_sna.features.members import member_features
from reddit_sna.models.activity_forecast import fit_activity_model, predict_activity_model
from reddit_sna.pipelines.controlled_pooling import LR, read_mean_cache
from tests.unit import test_hetco as member_fixture


def feature(month='2016-01',cid='c',size=2):
    return dict(reference_id='r',feature_month=month,community_id=cid,
                available_through_month=month,size=size,history_missing=1,density=1.)


def prediction(month='2016-02',model='p',seed=42,label='grow',guess='grow'):
    year,m=map(int,month.split('-'));prior=f'{year:04}-{m-1:02}'
    return dict(reference_id='r',feature_month=prior,community_id='c',label_month=month,
                label_reference_id='l',window='main',model=model,seed=seed,y_true=label,y_pred=guess,fallback=0)


class DiagnosticTests(unittest.TestCase):
    def test_coverage_separates_unresolved_censoring_and_mass(self):
        features=[feature(cid='e',size=8),feature(cid='u',size=2),feature('2016-02',size=10)]
        labels=[dict(reference_id='r',feature_month='2016-01',community_id=c,eligible=e,label=l,reason=reason)
                for c,e,l,reason in [('e','1','grow','one_to_one_size_comparison'),('u','0','','weak_overlap_unresolved')]]
        rows,_=coverage_tables(labels,features)
        allrow=next(r for r in rows if r['axis']=='all')
        self.assertEqual((allrow['observed'],allrow['eligible'],allrow['unresolved'],allrow['censored']),(2,1,1,1))
        self.assertEqual(allrow['coverage'],.5);self.assertEqual(allrow['member_month_coverage'],.8)
        terminal=next(r for r in rows if r['axis']=='month' and r['stratum']=='2016-02')
        self.assertIsNone(terminal['coverage'])

    def test_missing_nonterminal_or_duplicate_feature_is_rejected(self):
        for features in ([feature(),feature('2016-02')],[feature(),feature()]):
            with self.assertRaises(ValueError): coverage_tables([],features)

    def test_bad_feature_cutoff_and_graph_denominator_fail(self):
        f=feature();labels=[dict(reference_id='r',feature_month='2016-01',community_id='c',eligible='1',reason='ok')]
        with self.assertRaises(ValueError): coverage_tables(labels,[dict(f,available_through_month='2016-02')])
        with self.assertRaises(ValueError): coverage_tables(labels,[f],{'2016-01':dict(reply_endpoints=3)})

    def test_known_fixed_six_score_and_paired_errors(self):
        rows=[prediction(model='p'),prediction(model='r',guess='dissolve')]
        metrics,classes,_=forecast_tables(rows,[feature()])
        p=next(r for r in metrics if r['model']=='p' and r['axis']=='all')
        self.assertAlmostEqual(p['macro_f1_six'],1/6)
        self.assertEqual(next(r for r in classes if r['model']=='p' and r['axis']=='all' and r['label']=='grow')['support'],1)
        cases,intervals=paired_tables(rows,[feature()],[('p','r')])
        self.assertEqual(cases[0]['outcome'],'proposed_only');self.assertIsNone(intervals[0]['low'])

    def test_mismatched_keys_truth_or_duplicate_predictions_fail(self):
        for bad in ([prediction(),prediction()],
                    [prediction(),prediction(model='r',label='split')],
                    [prediction(),dict(prediction(model='r'),label_reference_id='different')]):
            with self.assertRaises(ValueError): prediction_units(bad)

    def test_month_blocks_are_paired_and_seeds_not_independent_units(self):
        rows=[];features=[]
        for i in range(2,8):
            month=f'2016-{i:02}'
            features.append(feature(f'2016-{i-1:02}'))
            for seed in (42,43):
                for model in ('p','r'): rows.append(prediction(month,model,seed))
        cases,intervals=paired_tables(rows,features,[('p','r')],draws=20)
        self.assertEqual(intervals[0]['months'],6)
        self.assertEqual((intervals[0]['low'],intervals[0]['high']),(0.,0.))
        self.assertEqual(len(cases),12)  # six repeated observations across two seeds

    def test_thirteen_means_and_invalid_bags(self):
        values=member_mean([list(range(13)),list(range(2,15))])
        self.assertEqual(len(values),13);self.assertEqual(values[MEAN_FIELDS[0]],1.)
        for bag in ([],[[]],[[0]*12],[[float('nan')]*13],[[float('inf')]*13]):
            with self.assertRaises(ValueError): member_mean(bag)

    def test_appending_future_records_preserves_all_past_means(self):
        groups={'2015-01':{'g':{'a','b'}},'2015-02':{'g':{'a','b'},'h':{'c'}}}
        outputs=[]
        for future in (False,True):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);member_fixture.MemberFeatureTests()._build(root,future)
                bags=member_features(root/'normalized.sqlite',root,sorted(groups),groups,extended=True)
                outputs.append({k:member_mean(v) for k,v in bags.items()})
        self.assertEqual(outputs[0],outputs[1])

    def test_cache_schema_and_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'cache.json').write_text(json.dumps(dict(source_manifests={'x':'h'},fields=[],sha256='invalid')))
            with self.assertRaises(ValueError):read_mean_cache(root,{'x':'h'})

    def test_single_class_training_never_learns_a_test_class(self):
        train=[dict(label='dissolve',label_month='2016-01',size=2)]
        test=[dict(label='grow',label_month='2016-02',size=100)]
        for hierarchical in (False,True):
            fitted=fit_activity_model(train,('size',),LR,hierarchical)
            labels,probs,flags=predict_activity_model(fitted,test)
            self.assertEqual(labels,['dissolve']);self.assertEqual(sum(probs[0]),1.)
            self.assertEqual(len(probs[0]),6);self.assertEqual(flags,[1])

    def test_scaler_is_fitted_only_to_training_rows(self):
        rows=[dict(label=l,label_month='2016-01',size=s) for l,s in [('grow',1),('dissolve',3),('grow',2),('dissolve',4)]]
        fitted=fit_activity_model(rows,('size',),LR)
        before=fitted['flat'][0].mean_.copy()
        predict_activity_model(fitted,[dict(size=1e9)])
        np.testing.assert_array_equal(before,fitted['flat'][0].mean_)
        self.assertEqual(before[0],2.5)
