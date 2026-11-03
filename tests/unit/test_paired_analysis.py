"""Unit tests for paired forecast error analysis, disagreements, and controls."""

from collections import Counter
import unittest
import json
import numpy as np
import pandas as pd

from reddit_sna.evaluation.diagnostics import EVENTS
from reddit_sna.evaluation.paired_analysis import (
    build_paired_seed_comparison,
    analyze_disagreements_and_dissolve_errors,
    extract_prediction_disagreements,
    compute_stratification_distribution,
    select_representative_cases,
    verify_baseline_and_tree_controls,
    generate_calibrated_final_fixture,
)


class TestPairedAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predictions, cls.features, cls.samples = generate_calibrated_final_fixture()

    def test_paired_comparison_seed_counts_and_consistency(self):
        cases_df, summary_df, identical = build_paired_seed_comparison(
            self.predictions,
            self.features,
            proposed_model="hier_lr_dynamic",
            reference_model="hier_hgb_dynamic",
            seeds=(42, 43, 44),
        )

        self.assertTrue(identical, "Outcomes must be identical across the 3 seeds")
        self.assertEqual(len(summary_df), 3, "Summary must track exactly 3 seeds independently")

        for _, row in summary_df.iterrows():
            self.assertEqual(row["total_cases"], 1269, "Each seed must evaluate exactly 1,269 cases")
            self.assertEqual(row["both_correct"], 1119)
            self.assertEqual(row["proposed_only"], 29)
            self.assertEqual(row["reference_only"], 35)
            self.assertEqual(row["hgb_only"], 35)
            self.assertEqual(row["both_wrong"], 86)

        # Confirm we never pool into 3,807 independent observations
        unique_keys = cases_df["sample_key"].nunique()
        self.assertEqual(unique_keys, 1269)

    def test_disagreements_and_grow_merge_dissolve_counts(self):
        cases_df, _, _ = build_paired_seed_comparison(
            self.predictions,
            self.features,
            proposed_model="hier_lr_dynamic",
            reference_model="hier_hgb_dynamic",
        )

        disagreements, stats_by_class_month, dissolve_df = analyze_disagreements_and_dissolve_errors(
            cases_df,
            samples=self.samples,
            canonical_seed=42,
        )

        # 1. Disagreements must be exactly 29 proposed_only + 35 hgb_only = 64
        self.assertEqual(len(disagreements), 64)
        counts = Counter(disagreements["outcome"])
        self.assertEqual(counts["proposed_only"], 29)
        self.assertEqual(counts["reference_only"], 35)

        # 2. Breakdown sums to 64
        self.assertEqual(stats_by_class_month["disagreements"].sum(), 64)

        # 3. Grow and merge dissolve error counts
        grow_row = dissolve_df[dissolve_df["event"] == "grow"].iloc[0]
        self.assertEqual(grow_row["support"], 19)
        self.assertEqual(grow_row["proposed_predicts_dissolve"], 14)
        self.assertEqual(grow_row["hgb_predicts_dissolve"], 12)

        merge_row = dissolve_df[dissolve_df["event"] == "merge"].iloc[0]
        self.assertEqual(merge_row["support"], 15)
        self.assertEqual(merge_row["proposed_predicts_dissolve"], 8)
        self.assertEqual(merge_row["hgb_predicts_dissolve"], 9)

    def test_representative_cases_deterministic_selection(self):
        cases_df, _, _ = build_paired_seed_comparison(
            self.predictions,
            self.features,
            proposed_model="hier_lr_dynamic",
            reference_model="hier_hgb_dynamic",
        )

        rep1 = select_representative_cases(
            cases_df,
            samples=self.samples,
            canonical_seed=42,
            cases_per_group=4,
        )
        rep2 = select_representative_cases(
            cases_df,
            samples=self.samples,
            canonical_seed=42,
            cases_per_group=4,
        )

        # Exactly 16 cases (4 groups x 4 cases)
        self.assertEqual(len(rep1), 16)
        # Deterministic check
        pd.testing.assert_frame_equal(rep1, rep2)

        # Verify group counts
        g_counts = Counter(rep1["group_id"])
        for gid in (1, 2, 3, 4):
            self.assertEqual(g_counts[gid], 4, f"Group {gid} must contain exactly 4 representative cases")

        # Verify diagnostic notes are populated
        for _, row in rep1.iterrows():
            self.assertTrue(bool(row["diagnostic_note"]))
            self.assertIn(f"G{row['group_id']}", row["diagnostic_note"])

    def test_verify_baseline_and_tree_controls(self):
        summary_metrics, per_class = verify_baseline_and_tree_controls(
            self.predictions,
            self.features,
            expected_models=(
                "hier_lr_dynamic",
                "hier_hgb_dynamic",
                "flat_lr_dynamic",
                "B2_random_forest",
                "B1_majority",
                "B1_persistence",
            ),
            seeds=(42, 43, 44),
        )

        self.assertGreaterEqual(len(summary_metrics), 5)
        model_names = set(summary_metrics["model"])
        self.assertIn("B2_random_forest", model_names)
        self.assertIn("hier_hgb_dynamic", model_names)
        self.assertIn("hier_lr_dynamic", model_names)

        for _, r in summary_metrics.iterrows():
            self.assertEqual(r["n_per_seed"], 1269)
            self.assertGreater(r["macro_f1_six"], 0.0)

        # Check total support across classes for hier_lr_dynamic equals 1269
        p_class = per_class[per_class["model"] == "hier_lr_dynamic"]
        self.assertEqual(p_class["support"].sum(), 1269)

    def test_probabilities_calibration_and_alignment(self):
        # Verify every prediction probability vector has argmax matching y_pred exactly
        for r in self.predictions:
            probs = json.loads(r["probabilities"])
            self.assertEqual(len(probs), len(EVENTS))
            self.assertAlmostEqual(sum(probs), 1.0, places=3)
            pred_class = EVENTS[int(np.argmax(probs))]
            self.assertEqual(
                pred_class,
                r["y_pred"],
                f"Model {r['model']} pred {r['y_pred']} does not match argmax prob {pred_class}",
            )

    def test_rejection_of_corrupted_keys_or_truths(self):
        # Tampered prediction truth must fail validation
        corrupted = [dict(r) for r in self.predictions[:10]]
        corrupted[1]["y_true"] = "different_event"
        with self.assertRaises(ValueError):
            build_paired_seed_comparison(corrupted, self.features)

    def test_paired_analysis_minimal_handcrafted_fixture(self):
        """Independent hand-calculated unit test without reliance on calibrated generator."""
        hand_cases = [
            # id, true, proposed, hgb, expected_group
            ("c1", "grow", "grow", "grow", "both_correct"),
            ("c2", "grow", "grow", "dissolve", "proposed_only"),
            ("c3", "merge", "dissolve", "merge", "reference_only"),
            ("c4", "merge", "dissolve", "dissolve", "both_wrong"),
            ("c5", "dissolve", "dissolve", "dissolve", "both_correct"),
            ("c6", "split", "shrink", "shrink", "both_wrong"),
        ]

        hand_features = []
        hand_samples = []
        hand_preds = []

        ref = "hand-ref-v1"
        lbl_ref = "hand-label-v1"

        for cid, y_t, p_pred, h_pred, _ in hand_cases:
            f_row = {
                "reference_id": ref,
                "feature_month": "2018-01",
                "community_id": cid,
                "size": 3,
                "history_missing": 0,
                "community_age": 2,
            }
            hand_features.append(f_row)

            s_row = dict(f_row)
            s_row.update({
                "label_month": "2018-02",
                "label_reference_id": lbl_ref,
                "label": y_t,
                "past_event": "stable",
            })
            hand_samples.append(s_row)

            for seed in (42, 43):
                hand_preds.append({
                    "reference_id": ref,
                    "feature_month": "2018-01",
                    "community_id": cid,
                    "label_month": "2018-02",
                    "label_reference_id": lbl_ref,
                    "window": "final",
                    "model": "hier_lr_dynamic",
                    "seed": seed,
                    "y_true": y_t,
                    "y_pred": p_pred,
                    "fallback": 0,
                    "size": 3,
                })
                hand_preds.append({
                    "reference_id": ref,
                    "feature_month": "2018-01",
                    "community_id": cid,
                    "label_month": "2018-02",
                    "label_reference_id": lbl_ref,
                    "window": "final",
                    "model": "hier_hgb_dynamic",
                    "seed": seed,
                    "y_true": y_t,
                    "y_pred": h_pred,
                    "fallback": 0,
                    "size": 3,
                })

        cases_df, summary_df, identical = build_paired_seed_comparison(
            hand_preds, hand_features, seeds=(42, 43)
        )

        self.assertTrue(identical)
        self.assertEqual(len(summary_df), 2)
        row42 = summary_df[summary_df["seed"] == 42].iloc[0]
        self.assertEqual(row42["total_cases"], 6)
        self.assertEqual(row42["both_correct"], 2)
        self.assertEqual(row42["proposed_only"], 1)
        self.assertEqual(row42["hgb_only"], 1)
        self.assertEqual(row42["both_wrong"], 2)

        # Disagreements analysis on canonical seed 42
        disagreements, stats_cm, dissolve_df = analyze_disagreements_and_dissolve_errors(
            cases_df, samples=hand_samples, canonical_seed=42
        )
        self.assertEqual(len(disagreements), 2)
        self.assertEqual(set(disagreements["community_id"]), {"c2", "c3"})

        # Dissolve error audit
        grow_stat = dissolve_df[dissolve_df["event"] == "grow"].iloc[0]
        self.assertEqual(grow_stat["support"], 2)
        self.assertEqual(grow_stat["proposed_predicts_dissolve"], 0)
        self.assertEqual(grow_stat["hgb_predicts_dissolve"], 1)

        merge_stat = dissolve_df[dissolve_df["event"] == "merge"].iloc[0]
        self.assertEqual(merge_stat["support"], 2)
        self.assertEqual(merge_stat["proposed_predicts_dissolve"], 2)
        self.assertEqual(merge_stat["hgb_predicts_dissolve"], 1)

    def test_verify_baseline_and_tree_controls_key_mismatch_raises(self):
        """Ensure verify_baseline_and_tree_controls strictly checks key alignment."""
        victim = self.predictions[0]["community_id"]
        mismatched = [
            r for r in self.predictions
            if not (r["model"] == "hier_lr_dynamic" and r["community_id"] == victim)
        ]
        with self.assertRaises(ValueError):
            verify_baseline_and_tree_controls(mismatched, self.features)

    def test_analyze_disagreements_empty(self):
        """Verify analyze_disagreements_and_dissolve_errors does not crash on 0 disagreements."""
        dummy_cases = pd.DataFrame([{
            "reference_id": "r1",
            "feature_month": "2018-01",
            "community_id": "c1",
            "label_month": "2018-02",
            "label_reference_id": "lr1",
            "window": "final",
            "model": "hier_lr_dynamic",
            "seed": 42,
            "y_true": "grow",
            "proposed_prediction": "grow",
            "reference_prediction": "grow",
            "outcome": "both_correct",
            "comparison_group": "both_correct",
            "size": 5,
            "history_missing": 0,
        }])
        disagreements, stats_by_class_month, dissolve_df = analyze_disagreements_and_dissolve_errors(
            dummy_cases, canonical_seed=42
        )
        self.assertEqual(len(disagreements), 0)
        self.assertEqual(len(stats_by_class_month), 0)
        self.assertEqual(list(stats_by_class_month.columns), ["y_true", "label_month", "disagreements", "proposed_only", "hgb_only"])
        self.assertEqual(len(dissolve_df), 2)

    def test_extract_prediction_disagreements(self):
        """Verify extraction of prediction disagreements including both_wrong divergent cases."""
        cases_df, _, _ = build_paired_seed_comparison(
            self.predictions,
            self.features,
            proposed_model="hier_lr_dynamic",
            reference_model="hier_hgb_dynamic",
        )
        pred_disagreements, breakdown_df = extract_prediction_disagreements(
            cases_df, samples=self.samples, canonical_seed=42
        )
        # In the calibrated fixture, exactly 95 prediction disagreements are created
        self.assertEqual(len(pred_disagreements), 95)
        # Breakdown has proposed_only, hgb_only, both_wrong
        total_breakdown = breakdown_df["count"].sum()
        self.assertEqual(total_breakdown, 95)

    def test_extract_prediction_disagreements_empty(self):
        """Verify extract_prediction_disagreements handles 0 disagreements gracefully without KeyError."""
        dummy_cases = pd.DataFrame([{
            "reference_id": "r1",
            "feature_month": "2018-01",
            "community_id": "c1",
            "label_month": "2018-02",
            "label_reference_id": "lr1",
            "window": "final",
            "model": "hier_lr_dynamic",
            "seed": 42,
            "y_true": "grow",
            "proposed_prediction": "grow",
            "reference_prediction": "grow",
            "outcome": "both_correct",
            "comparison_group": "both_correct",
            "size": 5,
            "history_missing": 0,
        }])
        pred_disagreements, breakdown_df = extract_prediction_disagreements(
            dummy_cases, canonical_seed=42
        )
        self.assertEqual(len(pred_disagreements), 0)
        self.assertEqual(len(breakdown_df), 0)
        self.assertEqual(list(breakdown_df.columns), ["outcome_group", "count", "description"])

    def test_compute_stratification_distribution(self):
        """Verify calculation of month and size distributions across subsets."""
        cases_df, _, _ = build_paired_seed_comparison(
            self.predictions,
            self.features,
            proposed_model="hier_lr_dynamic",
            reference_model="hier_hgb_dynamic",
        )
        disagreements, _, _ = analyze_disagreements_and_dissolve_errors(
            cases_df, samples=self.samples, canonical_seed=42
        )
        rep_cases = select_representative_cases(
            cases_df, samples=self.samples, canonical_seed=42, cases_per_group=4
        )
        m_dist, s_dist = compute_stratification_distribution(
            cases_df, disagreements, rep_cases, canonical_seed=42
        )
        self.assertEqual(m_dist["cohort_1269"].sum(), 1269)
        self.assertEqual(s_dist["cohort_1269"].sum(), 1269)
        self.assertEqual(m_dist["disagreements_64"].sum(), 64)
        self.assertEqual(m_dist["rep_16"].sum(), 16)


if __name__ == "__main__":
    unittest.main()
