"""Known denominators, causal member summaries and paired uncertainty controls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from reddit_sna.evaluation.diagnostics import coverage_tables, eligibility_comparison_tables, forecast_tables, paired_tables, paired_aggregation_tables, size_band, prediction_units, _smd, _ks_statistic,_cramers_v, paired_strata_bootstrap
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

    def test_coverage_distributions_include_quantiles_and_missingness(self):
        eligible_feature = dict(
            feature(cid="eligible", size=2),
            history_missing=1,
            context_history_missing=0,
            density=0.2,
            community_age=4,
            internal_weight=1.0,
            boundary_weight=2.0,
            records_per_member_log=1.5,
            past_window_fraction=0.4,
        )

        unresolved_feature = dict(
            feature(cid="unresolved", size=3),
            history_missing=0,
            context_history_missing=1,
            density=None,
            community_age=8,
            internal_weight=3.0,
            boundary_weight=4.0,
            records_per_member_log=2.5,
            past_window_fraction=0.6,
        )

        features = [eligible_feature, unresolved_feature]

        labels = [
            dict(
                reference_id="r",
                feature_month="2016-01",
                community_id="eligible",
                eligible="1",
                label="grow",
                reason="one_to_one_size_comparison",
            ),
            dict(
                reference_id="r",
                feature_month="2016-01",
                community_id="unresolved",
                eligible="0",
                label="",
                reason="weak_overlap_unresolved",
            ),
        ]

        _, distributions = coverage_tables(labels, features)

        eligible_density = next(
            row for row in distributions
            if row["axis"] == "all"
            and row["status"] == "eligible"
            and row["field"] == "density"
        )

        unresolved_density = next(
            row for row in distributions
            if row["axis"] == "all"
            and row["status"] == "unresolved"
            and row["field"] == "density"
        )

        self.assertEqual(eligible_density["n"], 1)
        self.assertEqual(unresolved_density["n"], 0)

        for row in (eligible_density, unresolved_density):
            self.assertTrue(
                {
                    "missing_n",
                    "missing_fraction",
                    "q25",
                    "q75",
                    "std",
                }.issubset(row)
            )

        self.assertEqual(eligible_density["missing_n"], 0)
        self.assertEqual(unresolved_density["missing_n"], 1)

        self.assertAlmostEqual(unresolved_density["missing_fraction"], 1.0)

        # Lineage history and member activity history are distinct fields.
        self.assertIn(
            ("eligible", "history_missing"),
            {
                (row["status"], row["field"])
                for row in distributions
                if row["axis"] == "all"
            },
        )
        self.assertIn(
            ("unresolved", "context_history_missing"),
            {
                (row["status"], row["field"])
                for row in distributions
                if row["axis"] == "all"
            },
        )

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

    def test_size_band_boundaries_and_invalid_values(self):
        self.assertEqual(size_band({"size": 1}), "singleton")
        self.assertEqual(size_band({"size": 2}), "2")
        self.assertEqual(size_band({"size": 3}), "3-4")
        self.assertEqual(size_band({"size": 4}), "3-4")
        self.assertEqual(size_band({"size": 5}), "5-20")
        self.assertEqual(size_band({"size": 20}), "5-20")
        self.assertEqual(size_band({"size": 21}), ">20")

        for invalid_size in [0, 2.5, -1, float("nan"), float("inf")]:
            with self.subTest(size=invalid_size):
                with self.assertRaises(ValueError):
                    size_band({"size": invalid_size})

    def test_forecast_tables_include_class_metrics_and_stratified_confusion(self):
        sizes = [2, 3, 5, 21]
        histories = [1, 0, 1, 0]

        features = []
        predictions = []

        for i, (size, history) in enumerate(zip(sizes, histories)):
            cid = f"community-{i}"

            features.append(
                dict(
                    feature(cid=cid, size=size),
                    history_missing=history,
                )
            )

            predictions.append(
                dict(
                    prediction(),
                    community_id=cid,
                )
            )

        metrics, classes, confusion = forecast_tables(
            predictions, features
        )

        # Every metric stratum must have six class records.
        for metric in metrics:
            matching = [
                row for row in classes
                if all(
                    row[k] == metric[k]
                    for k in ("window", "model", "seed", "axis", "stratum")
                )
            ]

            self.assertEqual(len(matching), 6)

            for row in matching:
                self.assertTrue(
                    {"precision", "recall", "f1", "support"}.issubset(row)
                )

        # Verify the four expected size-history combinations.
        size_history = {
            row["stratum"]
            for row in metrics
            if row["axis"] == "size_history"
        }

        self.assertEqual(
            size_history,
            {
                "2|missing",
                "3-4|available",
                "5-20|missing",
                ">20|available",
            },
        )

        # Every confusion table must contain 6 x 6 cells
        # and its counts must sum to the corresponding sample size.
        for metric in metrics:
            matching = [
                row for row in confusion
                if all(
                    row[k] == metric[k]
                    for k in ("window", "model", "seed", "axis", "stratum")
                )
            ]

            self.assertEqual(len(matching), 36)
            self.assertEqual(
                sum(row["count"] for row in matching),
                metric["n"],
            )

    def test_coverage_distributions_cover_all_required_strata(self):
        specifications = [
            ("c2", "2016-01", 2, 1, 0, "1"),
            ("c3", "2016-01", 3, 0, 1, "0"),
            ("c5", "2016-02", 5, 1, 1, "1"),
            ("c21", "2016-02", 21, 0, 0, "0"),
        ]

        features = []
        labels = []

        for cid, month, size, history, context, eligible in specifications:
            features.append(
                dict(
                    feature(month=month, cid=cid, size=size),
                    history_missing=history,
                    context_history_missing=context,
                    density=0.5,
                    community_age=3,
                )
            )

            labels.append(
                dict(
                    reference_id="r",
                    feature_month=month,
                    community_id=cid,
                    eligible=eligible,
                    label="grow" if eligible == "1" else "",
                    reason="one_to_one_size_comparison"
                    if eligible == "1"
                    else "weak_overlap_unresolved",
                )
            )

        _, distributions = coverage_tables(labels, features)

        size_rows = [
            row for row in distributions
            if row["field"] == "size"
        ]

        observed_strata = {
            (row["axis"], row["stratum"], row["status"])
            for row in size_rows
        }

        expected = {
            ("month", "2016-01", "eligible"),
            ("month", "2016-01", "unresolved"),
            ("month", "2016-02", "eligible"),
            ("month", "2016-02", "unresolved"),
            ("lineage_history", "missing", "eligible"),
            ("lineage_history", "available", "unresolved"),
            ("member_activity_history", "available", "eligible"),
            ("member_activity_history", "missing_or_not_recorded", "unresolved"),
            ("size_history", "2|missing", "eligible"),
            ("size_history", "3-4|available", "unresolved"),
            ("size_history", "5-20|missing", "eligible"),
            ("size_history", ">20|available", "unresolved"),
        }

        self.assertTrue(expected.issubset(observed_strata))

    def test_coverage_rejects_invalid_eligibility_values(self):
        f = feature()

        for invalid_value in ("unknown", "", "2", None):
            labels = [
                dict(
                    reference_id="r",
                    feature_month="2016-01",
                    community_id="c",
                    eligible=invalid_value,
                    label="",
                    reason="invalid_status",
                )
            ]

            with self.subTest(eligible=invalid_value):
                with self.assertRaises(ValueError):
                    coverage_tables(labels, [f])

    def test_forecast_tables_reject_duplicate_feature_keys(self):
        f = feature()
        duplicate_features = [f, dict(f)]

        with self.assertRaisesRegex(ValueError, "Duplicate feature key"):
            forecast_tables(
                [prediction()],
                duplicate_features,
            )


    def test_paired_tables_reject_duplicate_feature_keys(self):
        f = feature()
        duplicate_features = [f, dict(f)]

        predictions = [
            prediction(model="p"),
            prediction(model="r"),
        ]

        with self.assertRaisesRegex(ValueError, "Duplicate feature key"):
            paired_tables(
                predictions,
                duplicate_features,
                [("p", "r")],
            )


    def test_feature_map_rejects_missing_or_empty_keys(self):
        invalid_features = [
            dict(feature(), community_id=None),
            dict(feature(), community_id=""),
            {
                "reference_id": "r",
                "feature_month": "2016-01",
                "size": 2,
            },
        ]

        for invalid in invalid_features:
            with self.subTest(feature=invalid):
                with self.assertRaises(ValueError):
                    forecast_tables(
                        [prediction()],
                        [invalid],
                    )

    def test_smd_returns_zero_for_identical_distributions(self):
        left = [1, 2, 3, 4]
        right = [1, 2, 3, 4]

        self.assertAlmostEqual(_smd(left, right), 0.0)


    def test_smd_returns_signed_difference(self):
        left = [2, 3, 4, 5]
        right = [1, 2, 3, 4]

        self.assertGreater(_smd(left, right), 0.0)
        self.assertAlmostEqual(
            _smd(left, right),
            -_smd(right, left),
        )


    def test_smd_handles_insufficient_samples(self):
        self.assertIsNone(_smd([1], [1, 2]))
        self.assertIsNone(_smd([], [1, 2]))


    def test_smd_handles_zero_variance(self):
        self.assertEqual(_smd([2, 2, 2], [2, 2, 2]), 0.0)
        self.assertIsNone(_smd([2, 2, 2], [3, 3, 3]))


    def test_ks_statistic_returns_zero_for_identical_distributions(self):
        self.assertAlmostEqual(
            _ks_statistic([1, 2, 3], [1, 2, 3]),
            0.0,
        )


    def test_ks_statistic_returns_one_for_separated_samples(self):
        self.assertAlmostEqual(
            _ks_statistic([1, 2], [3, 4]),
            1.0,
        )


    def test_ks_statistic_is_symmetric(self):
        left = [1, 2, 3]
        right = [2, 4, 5]

        self.assertAlmostEqual(
            _ks_statistic(left, right),
            _ks_statistic(right, left),
        )


    def test_ks_statistic_handles_empty_samples(self):
        self.assertIsNone(_ks_statistic([], [1, 2]))
        self.assertIsNone(_ks_statistic([1, 2], []))


    def test_cramers_v_returns_zero_for_identical_category_proportions(self):
        left = ["A", "A", "B", "B"]
        right = ["A", "A", "B", "B"]

        self.assertAlmostEqual(_cramers_v(left, right), 0.0)


    def test_cramers_v_returns_one_for_perfect_category_separation(self):
        left = ["A", "A", "A", "A"]
        right = ["B", "B", "B", "B"]

        self.assertAlmostEqual(_cramers_v(left, right), 1.0)


    def test_cramers_v_returns_none_for_single_category(self):
        self.assertIsNone(
            _cramers_v(["A", "A"], ["A", "A"])
        )


    def test_cramers_v_accepts_mismatched_group_lengths(self):
        result = _cramers_v(
            ["A", "A", "B", "B"],
            ["A", "B", "B"],
        )

        self.assertIsNotNone(result)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)

    def test_smd_matches_expected_pooled_standard_deviation(self):
        left = [2, 4]
        right = [0, 2]

        # Mean difference = 2; pooled SD = sqrt(2).
        self.assertAlmostEqual(
            _smd(left, right),
            np.sqrt(2),
        )


    def test_ks_statistic_returns_expected_partial_difference(self):
        left = [1, 2, 3]
        right = [2, 3, 4]

        self.assertAlmostEqual(
            _ks_statistic(left, right),
            1 / 3,
        )


    def test_cramers_v_is_symmetric(self):
        left = ["A", "A", "B", "B"]
        right = ["A", "B", "B", "B"]

        self.assertAlmostEqual(
            _cramers_v(left, right),
            _cramers_v(right, left),
        )


    def test_cramers_v_handles_unequal_group_sizes(self):
        left = ["A", "A", "B", "B"]
        right = ["A", "A", "A", "A", "B", "B", "B", "B"]

        self.assertAlmostEqual(
            _cramers_v(left, right),
            0.0,
        )


    def test_cramers_v_returns_none_for_empty_groups(self):
        self.assertIsNone(_cramers_v([], []))
        self.assertIsNone(_cramers_v([], ["A", "B"]))

    def test_eligibility_comparison_returns_expected_methods(self):
        specifications = [
            ("c1", 2, 1, 0, "1"),
            ("c2", 3, 0, 1, "0"),
            ("c3", 5, 1, 1, "1"),
            ("c4", 21, 0, 0, "0"),
        ]

        features = []
        labels = []

        for cid, size, history, context, eligible in specifications:
            features.append(
                dict(
                    feature(cid=cid, size=size),
                    history_missing=history,
                    context_history_missing=context,
                    density=0.5,
                    community_age=3,
                    internal_weight=10,
                    boundary_weight=5,
                    records_per_member_log=1.5,
                    past_window_fraction=0.5,
                )
            )

            labels.append(
                dict(
                    reference_id="r",
                    feature_month="2016-01",
                    community_id=cid,
                    eligible=eligible,
                    label="grow" if eligible == "1" else "",
                    reason="test",
                )
            )

        rows = eligibility_comparison_tables(labels, features)

        methods = {
            (row["field"], row["method"])
            for row in rows
            if row["axis"] == "all"
        }

        self.assertIn(("size", "smd"), methods)
        self.assertIn(("size", "ks"), methods)
        self.assertIn(("density", "smd"), methods)
        self.assertIn(("density", "ks"), methods)
        self.assertIn(("history_missing", "cramers_v"), methods)
        self.assertIn(("context_history_missing", "cramers_v"), methods)

        self.assertEqual(
            {
                row["axis"]
                for row in rows
            },
            {
                "all",
                "month",
                "size",
                "lineage_history",
                "member_activity_history",
                "size_history",
            },
        )


    def test_eligibility_comparison_excludes_final_censored_features(self):
        f1 = dict(
            feature(cid="c1"),
            history_missing=0,
            context_history_missing=0,
            density=0.5,
        )

        f2 = dict(
            feature(cid="c2", month="2016-02"),
            history_missing=0,
            context_history_missing=0,
            density=0.8,
        )

        labels = [
            dict(
                reference_id="r",
                feature_month="2016-01",
                community_id="c1",
                eligible="1",
                label="grow",
                reason="test",
            )
        ]

        rows = eligibility_comparison_tables(labels, [f1, f2])

        overall = next(
            row for row in rows
            if row["axis"] == "all"
            and row["field"] == "size"
            and row["method"] == "smd"
        )

        self.assertEqual(overall["eligible_n"], 1)
        self.assertEqual(overall["unresolved_n"], 0)


    def test_eligibility_comparison_reports_missing_values(self):
        f1 = dict(
            feature(cid="c1"),
            history_missing=0,
            context_history_missing=0,
            density=None,
        )

        f2 = dict(
            feature(cid="c2"),
            history_missing=1,
            context_history_missing=1,
            density=0.5,
        )

        labels = [
            dict(
                reference_id="r",
                feature_month="2016-01",
                community_id="c1",
                eligible="1",
                label="grow",
                reason="test",
            ),
            dict(
                reference_id="r",
                feature_month="2016-01",
                community_id="c2",
                eligible="0",
                label="",
                reason="unresolved",
            ),
        ]

        rows = eligibility_comparison_tables(labels, [f1, f2])

        density = next(
            row for row in rows
            if row["axis"] == "all"
            and row["field"] == "density"
            and row["method"] == "smd"
        )

        self.assertEqual(density["eligible_missing_n"], 1)
        self.assertEqual(density["unresolved_missing_n"], 0)
        self.assertEqual(density["eligible_valid_n"], 0)
        self.assertEqual(density["unresolved_valid_n"], 1)
        self.assertIsNone(density["statistic"])


    def test_eligibility_comparison_rejects_duplicate_label_keys(self):
        f = dict(
            feature(),
            history_missing=0,
            context_history_missing=0,
        )

        label = dict(
            reference_id="r",
            feature_month="2016-01",
            community_id="c",
            eligible="1",
            label="grow",
            reason="test",
        )

        with self.assertRaisesRegex(ValueError, "Duplicate label key"):
            eligibility_comparison_tables(
                [label, dict(label)],
                [f],
            )

    def test_eligibility_comparison_rejects_label_without_feature(self):
        label = dict(
            reference_id="r",
            feature_month="2016-01",
            community_id="missing",
            eligible="1",
            label="grow",
            reason="test",
        )

        with self.assertRaisesRegex(
            ValueError,
            "matching feature/label keys",
        ):
            eligibility_comparison_tables(
                [label],
                [dict(
                    feature(),
                    history_missing=0,
                    context_history_missing=0,
                )],
            )

    def test_eligibility_comparison_rejects_nonterminal_unlabeled_feature(self):
        f1 = dict(
            feature(cid="c1", month="2016-01"),
            history_missing=0,
            context_history_missing=0,
        )
        f2 = dict(
            feature(cid="c2", month="2016-02"),
            history_missing=0,
            context_history_missing=0,
        )

        labels = [
            dict(
                reference_id="r",
                feature_month="2016-02",
                community_id="c2",
                eligible="1",
                label="grow",
                reason="test",
            )
        ]

        with self.assertRaisesRegex(
            ValueError,
            "Only the final snapshot can lack target rows",
        ):
            eligibility_comparison_tables(labels, [f1, f2])

    def test_paired_aggregation_averages_seed_rates_not_case_counts(self):
        cases = []

        outcomes = {
            42: ("proposed_only", "both_correct"),
            43: ("reference_only", "both_wrong"),
        }

        for seed, seed_outcomes in outcomes.items():
            for i, outcome in enumerate(seed_outcomes):
                cases.append(
                    dict(
                        reference_id="r",
                        feature_month=f"2016-0{i + 1}",
                        community_id=f"c{i + 1}",
                        label_month=f"2016-0{i + 2}",
                        label_reference_id="r",
                        window="final",
                        proposed="p",
                        reference="r",
                        seed=seed,
                        y_true="grow",
                        outcome=outcome,
                        size=2,
                        size_band="2",
                        history_missing=0,
                        context_history_missing=0,
                    )
                )

        summary, per_seed = paired_aggregation_tables(cases)

        overall = next(
            row for row in summary
            if row["axis"] == "all"
        )

        self.assertEqual(overall["seed_count"], 2)
        self.assertEqual(overall["n_community_months"], 2)

        for outcome in (
            "both_correct",
            "proposed_only",
            "reference_only",
            "both_wrong",
        ):
            self.assertAlmostEqual(
                overall[f"mean_{outcome}_rate"],
                0.25,
            )

        self.assertEqual(len([
            row for row in per_seed
            if row["axis"] == "all"
        ]), 2)


    def test_paired_aggregation_rejects_duplicate_seed_case(self):
        case = dict(
            reference_id="r",
            feature_month="2016-01",
            community_id="c",
            label_month="2016-02",
            label_reference_id="r",
            window="final",
            proposed="p",
            reference="r",
            seed=42,
            y_true="grow",
            outcome="proposed_only",
            size=2,
            size_band="2",
            history_missing=0,
            context_history_missing=0,
        )

        with self.assertRaisesRegex(ValueError, "Duplicate paired case"):
            paired_aggregation_tables([case, dict(case)])

    def test_paired_aggregation_rejects_different_seed_key_sets(self):
        base = dict(
            reference_id="r",
            feature_month="2016-01",
            community_id="c",
            label_month="2016-02",
            label_reference_id="r",
            window="final",
            proposed="p",
            reference="r",
            y_true="grow",
            outcome="proposed_only",
            size=2,
            size_band="2",
            history_missing=0,
            context_history_missing=0,
        )

        cases = [
            dict(base, seed=42),
            dict(base, seed=43, community_id="different"),
        ]

        with self.assertRaisesRegex(
            ValueError,
            "identical community-month keys",
        ):
            paired_aggregation_tables(cases)


    def test_paired_aggregation_rejects_seed_metadata_mismatch(self):
        base = dict(
            reference_id="r",
            feature_month="2016-01",
            community_id="c",
            label_month="2016-02",
            label_reference_id="r",
            window="final",
            proposed="p",
            reference="r",
            y_true="grow",
            outcome="proposed_only",
            size=2,
            size_band="2",
            history_missing=0,
            context_history_missing=0,
        )

        cases = [
            dict(base, seed=42),
            dict(base, seed=43, size=10),
        ]

        with self.assertRaisesRegex(
            ValueError,
            "metadata differs",
        ):
            paired_aggregation_tables(cases)


    def test_paired_strata_bootstrap_averages_seeds_and_preserves_calendar_gaps(self):
        cases = []
        months = (
            "2016-01",
            "2016-02",
            "2016-04",
            "2016-05",
            "2016-06",
            "2016-07",
        )

        for index, month in enumerate(months):
            for seed, outcome in (
                (42, "proposed_only"),
                (43, "both_correct"),
            ):
                cases.append(
                    dict(
                        reference_id="r",
                        feature_month=f"2015-{index + 1:02d}",
                        community_id=f"c{index}",
                        label_month=month,
                        label_reference_id="r",
                        window="final",
                        proposed="p",
                        reference="r",
                        seed=seed,
                        y_true="grow",
                        outcome=outcome,
                        size=2,
                        size_band="2",
                        history_missing=0,
                        context_history_missing=0,
                    )
                )

        rows = paired_strata_bootstrap(
            cases,
            draws=30,
            block_length=2,
            bootstrap_seed=123,
        )

        overall = [
            row for row in rows
            if row["axis"] == "all"
        ]

        self.assertEqual(len(overall), 4)

        proposed_only = next(
            row for row in overall
            if row["outcome"] == "proposed_only"
        )

        both_correct = next(
            row for row in overall
            if row["outcome"] == "both_correct"
        )

        self.assertAlmostEqual(proposed_only["mean_rate"], 0.5)
        self.assertAlmostEqual(both_correct["mean_rate"], 0.5)

        self.assertEqual(proposed_only["n_community_months"], 6)
        self.assertEqual(proposed_only["seed_count"], 2)

        # March is absent from observations but remains on the
        # original calendar axis between February and April.
        self.assertEqual(proposed_only["months"], 7)

        self.assertEqual(proposed_only["valid_draws"], 30)
        self.assertEqual(
            proposed_only["bootstrap_method"],
            "paired_calendar_month_blocks",
        )

        self.assertAlmostEqual(proposed_only["ci_low"], 0.5)
        self.assertAlmostEqual(proposed_only["ci_high"], 0.5)


    def test_paired_strata_bootstrap_returns_no_ci_for_short_timeline(self):
        cases = []

        for index, month in enumerate(
            ("2016-01", "2016-02", "2016-03")
        ):
            for seed in (42, 43):
                cases.append(
                    dict(
                        reference_id="r",
                        feature_month=f"2015-{index + 1:02d}",
                        community_id=f"c{index}",
                        label_month=month,
                        label_reference_id="r",
                        window="final",
                        proposed="p",
                        reference="r",
                        seed=seed,
                        y_true="grow",
                        outcome="proposed_only",
                        size=2,
                        size_band="2",
                        history_missing=0,
                        context_history_missing=0,
                    )
                )

        rows = paired_strata_bootstrap(cases, draws=20)

        overall = [
            row for row in rows
            if row["axis"] == "all"
        ]

        self.assertEqual(len(overall), 4)

        for row in overall:
            self.assertIsNone(row["ci_low"])
            self.assertIsNone(row["ci_high"])
            self.assertEqual(row["valid_draws"], 0)
            self.assertEqual(
                row["reason"],
                "fewer_than_six_calendar_months",
            )


    def test_paired_strata_bootstrap_rejects_invalid_parameters(self):
        cases = []

        for index in range(6):
            for seed in (42, 43):
                cases.append(
                    dict(
                        reference_id="r",
                        feature_month=f"2015-{index + 1:02d}",
                        community_id=f"c{index}",
                        label_month=f"2016-{index + 1:02d}",
                        label_reference_id="r",
                        window="final",
                        proposed="p",
                        reference="r",
                        seed=seed,
                        y_true="grow",
                        outcome="proposed_only",
                        size=2,
                        size_band="2",
                        history_missing=0,
                        context_history_missing=0,
                    )
                )

        with self.assertRaisesRegex(ValueError, "draws"):
            paired_strata_bootstrap(cases, draws=0)

        with self.assertRaisesRegex(ValueError, "block_length"):
            paired_strata_bootstrap(cases, block_length=0)


    def test_paired_strata_bootstrap_is_reproducible_and_rates_are_valid(self):
        cases = []
        for index in range(6):
            month = f"2016-{index + 1:02d}"

            for seed in (42, 43):
                outcome = (
                    "proposed_only"
                    if (index + seed) % 2 == 0
                    else "both_correct"
                )

                cases.append(
                    dict(
                        reference_id="r",
                        feature_month=f"2015-{index + 1:02d}",
                        community_id=f"c{index}",
                        label_month=month,
                        label_reference_id="r",
                        window="final",
                        proposed="p",
                        reference="r",
                        seed=seed,
                        y_true="grow",
                        outcome=outcome,
                        size=2,
                        size_band="2",
                        history_missing=0,
                        context_history_missing=0,
                    )
                )

        first = paired_strata_bootstrap(
            cases,
            draws=50,
            block_length=2,
            bootstrap_seed=12345,
        )

        second = paired_strata_bootstrap(
            cases,
            draws=50,
            block_length=2,
            bootstrap_seed=12345,
        )

        self.assertEqual(first, second)

        groups = {}

        for row in first:
            key = (row["axis"], row["stratum"])
            groups.setdefault(key, []).append(row)

            self.assertGreaterEqual(row["mean_rate"], 0.0)
            self.assertLessEqual(row["mean_rate"], 1.0)

            if row["ci_low"] is not None:
                self.assertGreaterEqual(row["ci_low"], 0.0)
                self.assertLessEqual(row["ci_low"], 1.0)
                self.assertGreaterEqual(row["ci_high"], 0.0)
                self.assertLessEqual(row["ci_high"], 1.0)
                self.assertLessEqual(row["ci_low"], row["ci_high"])

        for rows in groups.values():
            self.assertEqual(len(rows), 4)

            total_rate = sum(row["mean_rate"] for row in rows)
            self.assertAlmostEqual(total_rate, 1.0, places=10)
