"""Unit tests for week 4 general comparative evaluation tool."""

import csv
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from reddit_sna.evaluation.diagnostics import EVENTS, KEY
from reddit_sna.evaluation.paired_analysis import generate_calibrated_final_fixture
from reddit_sna.evaluation.week4_comparison import (
    MODEL_ROLE_MAP,
    compute_paired_wins_losses,
    compute_per_class_and_monthly_tables,
    compute_primary_comparison_table,
    evaluate_target_cases,
    reconcile_week4_reproducibility,
)


class TestWeek4Comparison(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calibrated_preds, cls.calibrated_feats, cls.calibrated_samps = generate_calibrated_final_fixture()
        cls.project_root = Path(__file__).resolve().parents[2]
        cls.handoff_p = cls.project_root / "artifacts/handoff/tam-f1-20261104/export/predictions_final.csv"

    def test_handcrafted_small_fixture_wins_losses(self):
        """Verify exact wins, losses, both_correct, both_wrong on a hand-crafted 8-case fixture."""
        # 8 cases:
        # Case 0: yt=dissolve, p=dissolve, c=dissolve -> both_correct
        # Case 1: yt=grow,     p=grow,     c=dissolve -> proposed_only (win)
        # Case 2: yt=merge,    p=dissolve, c=merge    -> reference_only (loss)
        # Case 3: yt=shrink,   p=dissolve, c=split    -> both_wrong
        # Case 4: yt=split,    p=split,    c=split    -> both_correct
        # Case 5: yt=grow,     p=dissolve, c=grow     -> reference_only (loss)
        # Case 6: yt=merge,    p=merge,    c=dissolve -> proposed_only (win)
        # Case 7: yt=shrink,   p=shrink,   c=shrink   -> both_correct
        spec = [
            ("dissolve", "dissolve", "dissolve", "2017-12", "2018-01"),
            ("grow",     "grow",     "dissolve", "2017-12", "2018-01"),
            ("merge",    "dissolve", "merge",    "2018-01", "2018-02"),
            ("shrink",   "dissolve", "split",    "2018-01", "2018-02"),
            ("split",    "split",    "split",    "2018-02", "2018-03"),
            ("grow",     "dissolve", "grow",     "2018-02", "2018-03"),
            ("merge",    "merge",    "dissolve", "2018-03", "2018-04"),
            ("shrink",   "shrink",   "shrink",   "2018-03", "2018-04"),
        ]

        small_preds = []
        for i, (yt, p_pred, c_pred, fm, lm) in enumerate(spec):
            base_row = {
                "reference_id": "ref1",
                "feature_month": fm,
                "community_id": f"comm_{i}",
                "label_month": lm,
                "label_reference_id": f"lref_{i}",
                "size": "5-20",
                "seed": 42,
                "y_true": yt,
                "window": "final",
                "probabilities": {},
            }
            # Proposed row
            p_row = dict(base_row)
            p_row["model"] = "model_A"
            p_row["y_pred"] = p_pred
            small_preds.append(p_row)

            # Comparator row
            c_row = dict(base_row)
            c_row["model"] = "model_B"
            c_row["y_pred"] = c_pred
            small_preds.append(c_row)

        summary_df, by_class_df, by_month_df, case_details = compute_paired_wins_losses(
            small_preds,
            proposed_model="model_A",
            comparator_models=["model_B"],
            seeds=(42,),
            window="final",
        )

        self.assertEqual(len(summary_df), 1)
        row = summary_df.iloc[0]
        self.assertEqual(row["total_cases"], 8)
        self.assertEqual(row["both_correct"], 3)
        self.assertEqual(row["proposed_only (wins)"], 2)
        self.assertEqual(row["reference_only (losses)"], 2)
        self.assertEqual(row["both_wrong"], 1)
        self.assertEqual(row["net_wins"], 0)

        # Verify by class breakdown
        grow_row = by_class_df[(by_class_df["y_true"] == "grow") & (by_class_df["seed"] == 42)].iloc[0]
        self.assertEqual(grow_row["wins"], 1)
        self.assertEqual(grow_row["losses"], 1)
        self.assertEqual(grow_row["net"], 0)

        merge_row = by_class_df[(by_class_df["y_true"] == "merge") & (by_class_df["seed"] == 42)].iloc[0]
        self.assertEqual(merge_row["wins"], 1)
        self.assertEqual(merge_row["losses"], 1)
        self.assertEqual(merge_row["net"], 0)

        shrink_row = by_class_df[(by_class_df["y_true"] == "shrink") & (by_class_df["seed"] == 42)].iloc[0]
        self.assertEqual(shrink_row["both_correct"], 1)
        self.assertEqual(shrink_row["both_wrong"], 1)
        self.assertEqual(shrink_row["wins"], 0)
        self.assertEqual(shrink_row["losses"], 0)

        # Verify by month breakdown
        m1_row = by_month_df[(by_month_df["label_month"] == "2018-01") & (by_month_df["seed"] == 42)].iloc[0]
        self.assertEqual(m1_row["both_correct"], 1)
        self.assertEqual(m1_row["wins"], 1)
        self.assertEqual(m1_row["losses"], 0)
        self.assertEqual(m1_row["net"], 1)

    def test_missing_proposed_model_raises_value_error(self):
        """Ensure missing proposed model raises an explicit ValueError."""
        with self.assertRaises(ValueError):
            compute_primary_comparison_table(
                self.calibrated_preds,
                proposed_model="non_existent_model_xyz",
            )

        with self.assertRaises(ValueError):
            compute_paired_wins_losses(
                self.calibrated_preds,
                proposed_model="non_existent_model_xyz",
                comparator_models=["hier_hgb_dynamic"],
            )

        with self.assertRaises(ValueError):
            evaluate_target_cases(
                self.calibrated_preds,
                proposed_model="non_existent_model_xyz",
            )

    def test_target_cases_predeclared_evaluation(self):
        """Test evaluation when pre-declared target cases are provided."""
        rows = [
            # Case 1: old wrong (dissolve), new correct (grow) -> repaired
            {
                "reference_id": "ref", "feature_month": "2018-01", "community_id": "c1",
                "label_month": "2018-02", "label_reference_id": "lref", "size": "5-20",
                "model": "hier_lr_dynamic", "seed": 42, "y_true": "grow", "y_pred": "dissolve", "window": "final"
            },
            {
                "reference_id": "ref", "feature_month": "2018-01", "community_id": "c1",
                "label_month": "2018-02", "label_reference_id": "lref", "size": "5-20",
                "model": "new_proposed", "seed": 42, "y_true": "grow", "y_pred": "grow", "window": "final"
            },
            # Case 2: old correct (merge), new wrong (dissolve) -> broken
            {
                "reference_id": "ref", "feature_month": "2018-01", "community_id": "c2",
                "label_month": "2018-02", "label_reference_id": "lref", "size": "5-20",
                "model": "hier_lr_dynamic", "seed": 42, "y_true": "merge", "y_pred": "merge", "window": "final"
            },
            {
                "reference_id": "ref", "feature_month": "2018-01", "community_id": "c2",
                "label_month": "2018-02", "label_reference_id": "lref", "size": "5-20",
                "model": "new_proposed", "seed": 42, "y_true": "merge", "y_pred": "dissolve", "window": "final"
            },
        ]
        key1 = ("ref", "2018-01", "c1", "2018-02", "lref")
        key2 = ("ref", "2018-01", "c2", "2018-02", "lref")

        res = evaluate_target_cases(
            rows,
            target_cases_keys={key1, key2},
            proposed_model="new_proposed",
            old_proposed_model="hier_lr_dynamic",
            canonical_seed=42,
        )

        self.assertTrue(res["provided"])
        self.assertFalse(res["is_descriptive_only"])
        self.assertEqual(res["total_cases"], 2)
        self.assertEqual(res["repaired_cases"], 1)
        self.assertEqual(res["broken_cases"], 1)
        self.assertEqual(res["correct_old"], 1)
        self.assertEqual(res["correct_new"], 1)
        self.assertEqual(res["confusion_new"]["grow"]["grow"], 1)
        self.assertEqual(res["confusion_new"]["merge"]["dissolve"], 1)

    def test_target_cases_fallback_when_unprovided(self):
        """Test strict descriptive fallback to 34 grow/merge cases when unsupplied."""
        res = evaluate_target_cases(
            self.calibrated_preds,
            target_cases_keys=None,
            proposed_model="hier_lr_dynamic",
            old_proposed_model="hier_lr_dynamic",
            canonical_seed=42,
        )

        self.assertFalse(res["provided"])
        self.assertTrue(res["is_descriptive_only"])
        self.assertEqual(res["label"], "DESCRIPTIVE ONLY - target set not pre-declared by owner")
        self.assertEqual(res["total_cases"], 34)
        self.assertEqual(res["dissolve_predicted_old"], 22)
        self.assertEqual(res["dissolve_predicted_new"], 22)
        self.assertEqual(res["breakdown"]["grow"]["support"], 19)
        self.assertEqual(res["breakdown"]["grow"]["dissolve_old"], 14)
        self.assertEqual(res["breakdown"]["merge"]["support"], 15)
        self.assertEqual(res["breakdown"]["merge"]["dissolve_old"], 8)

    def test_primary_comparison_table_generation(self):
        """Test primary baseline table generation on calibrated fixture."""
        summary_df, missing_models = compute_primary_comparison_table(
            self.calibrated_preds,
            proposed_model="hier_lr_dynamic",
            seeds=(42, 43, 44),
        )

        self.assertIn("hier_lr_dynamic", summary_df["model"].values)
        self.assertIn("hier_hgb_dynamic", summary_df["model"].values)

        p_row = summary_df[summary_df["model"] == "hier_lr_dynamic"].iloc[0]
        self.assertEqual(p_row["n_per_seed"], 1269)
        self.assertGreater(p_row["macro_f1_mean"], 0.0)
        self.assertEqual(p_row["macro_f1_sd"], 0.0)

        # Missing models list should include models in default list not in calibrated fixture
        self.assertIn("B4_logreg", missing_models)
        self.assertIn("B5_matched_boosting", missing_models)

    def test_per_class_and_monthly_tables(self):
        """Test per-class and monthly breakdown calculations."""
        per_class_df, per_month_df = compute_per_class_and_monthly_tables(
            self.calibrated_preds,
            models=["hier_lr_dynamic", "hier_hgb_dynamic"],
            seeds=(42, 43, 44),
        )

        # Check grow and merge metrics for hier_lr_dynamic
        lr_grow = per_class_df[(per_class_df["model"] == "hier_lr_dynamic") & (per_class_df["label"] == "grow")].iloc[0]
        self.assertEqual(lr_grow["support"], 19)
        self.assertEqual(lr_grow["to_dissolve"], 14)
        self.assertAlmostEqual(lr_grow["to_dissolve_rate"], 14 / 19, places=4)

        lr_merge = per_class_df[(per_class_df["model"] == "hier_lr_dynamic") & (per_class_df["label"] == "merge")].iloc[0]
        self.assertEqual(lr_merge["support"], 15)
        self.assertEqual(lr_merge["to_dissolve"], 8)
        self.assertAlmostEqual(lr_merge["to_dissolve_rate"], 8 / 15, places=4)

        # Monthly table should have 9 months (Jan to Sep 2018)
        lr_months = per_month_df[per_month_df["model"] == "hier_lr_dynamic"]
        self.assertEqual(len(lr_months), 9)
        self.assertEqual(lr_months["support"].sum(), 1269)

    def test_calibrated_reconciliation_exact_numbers(self):
        """Test that reconciliation counts 1119/29/35/86 and 64 contrast cases."""
        rec = reconcile_week4_reproducibility(
            self.calibrated_preds,
            handoff_dir=None,
            proposed_model="hier_lr_dynamic",
            canonical_seed=42,
        )

        self.assertEqual(rec["both_correct"], 1119)
        self.assertEqual(rec["proposed_only"], 29)
        self.assertEqual(rec["hgb_only"], 35)
        self.assertEqual(rec["both_wrong"], 86)
        self.assertEqual(rec["contrast_cases"], 64)
        self.assertTrue(rec["expected_4group_pass"])

    def test_real_handoff_reconciliation(self):
        """If real handoff is extracted, verify full reconciliation against ground truth."""
        if not self.handoff_p.is_file():
            self.skipTest("Real handoff export/predictions_final.csv not found")

        with self.handoff_p.open("r", encoding="utf-8") as f:
            real_preds = list(csv.DictReader(f))

        rec = reconcile_week4_reproducibility(
            real_preds,
            handoff_dir=self.handoff_p.parent.parent,
            proposed_model="hier_lr_dynamic",
            canonical_seed=42,
        )

        self.assertEqual(rec["status"], "PASS")
        self.assertEqual(rec["both_correct"], 1119)
        self.assertEqual(rec["proposed_only"], 29)
        self.assertEqual(rec["hgb_only"], 35)
        self.assertEqual(rec["both_wrong"], 86)
        self.assertEqual(rec["contrast_cases"], 64)
        self.assertTrue(rec["expected_4group_pass"])
        self.assertTrue(rec["f1_match_pass"])
        self.assertTrue(rec["c64_keys_match"])
        self.assertAlmostEqual(rec["proposed_macro_f1"], 0.4117, places=4)
        self.assertAlmostEqual(rec["hgb_macro_f1"], 0.3880, places=4)


if __name__ == "__main__":
    unittest.main()
