"""Unit tests for LR-HGB cross-cohort comparative evaluation and paired block-bootstrap.

Verifies:
1. Fixed six-class Macro-F1 calculation when classes are absent (support=0, zero_division=0).
2. Paired block-bootstrap resampling evaluates both models on identical month blocks.
3. Key and label alignment enforcement between proposed and reference models.
4. Exact full-study delta and 95% confidence interval reproduction from frozen predictions.
"""

import json
import math
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from reddit_sna.evaluation.cross_cohort_comparison import (
    calculate_six_class_macro_f1,
    paired_block_bootstrap_comparison,
    validate_paired_alignment,
)
from reddit_sna.evaluation.diagnostics import EVENTS
from reddit_sna.evaluation.paired_analysis import generate_calibrated_final_fixture


class TestLRHGBCrossCohort(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calibrated_preds, cls.calibrated_feats, cls.calibrated_samps = generate_calibrated_final_fixture()
        cls.project_root = Path(__file__).resolve().parents[2]
        cls.handoff_p = cls.project_root / "artifacts/handoff/tam-f1-20261104/export/predictions_final.csv"

    def test_macro_f1_with_absent_classes(self):
        """Test that Macro-F1 strictly averages across all 6 classes when classes are absent."""
        # Create dataset with ONLY 2 classes: 'grow' and 'dissolve'
        # 'stable', 'shrink', 'merge', 'split' have 0 support
        y_true = ["grow", "grow", "dissolve", "dissolve", "dissolve", "dissolve"]
        y_pred = ["grow", "dissolve", "dissolve", "dissolve", "dissolve", "grow"]

        res = calculate_six_class_macro_f1(y_true, y_pred)

        self.assertEqual(res["n"], 6)
        # grow: tp=1, fp=1, fn=1 -> prec=0.5, rec=0.5, f1=0.5
        # dissolve: tp=3, fp=1, fn=1 -> prec=0.75, rec=0.75, f1=0.75
        self.assertAlmostEqual(res["per_class"]["grow"]["f1"], 0.5, places=4)
        self.assertAlmostEqual(res["per_class"]["dissolve"]["f1"], 0.75, places=4)

        # Absent classes must have support=0, f1=0.0, precision=0.0, recall=0.0 (zero_division=0)
        for absent in ["stable", "shrink", "merge", "split"]:
            self.assertEqual(res["per_class"][absent]["support"], 0)
            self.assertEqual(res["per_class"][absent]["f1"], 0.0)
            self.assertEqual(res["per_class"][absent]["precision"], 0.0)
            self.assertEqual(res["per_class"][absent]["recall"], 0.0)

        # macro_f1_six MUST divide by all 6 classes: (0.5 + 0.75 + 0 + 0 + 0 + 0) / 6 = 1.25 / 6 = 0.20833
        expected_macro_six = (0.5 + 0.75) / 6.0
        self.assertAlmostEqual(res["macro_f1_six"], expected_macro_six, places=4)

        # macro_f1_present divides ONLY by present classes (2): (0.5 + 0.75) / 2 = 0.625
        expected_macro_present = (0.5 + 0.75) / 2.0
        self.assertAlmostEqual(res["macro_f1_present"], expected_macro_present, places=4)

        # Crucial check: macro_f1_six is strictly lower than macro_f1_present under absent classes
        self.assertNotEqual(res["macro_f1_six"], res["macro_f1_present"])
        self.assertLess(res["macro_f1_six"], res["macro_f1_present"])

    def test_paired_block_bootstrap_shared_months(self):
        """Test paired block-bootstrap evaluates both models on identical resampled month blocks."""
        months = [f"2018-{m:02d}" for m in range(1, 10)]  # 9 evaluation months
        prev_months = ["2017-12"] + [f"2018-{m:02d}" for m in range(1, 8 + 1)]

        # Build balanced 9-month mock data with 2 models: 'model_A' and 'model_B'
        mock_preds = []
        for m_idx, m in enumerate(months):
            f_month = prev_months[m_idx]
            for cid in range(10):
                # Model A predicts dissolve and grow correctly
                # Model B predicts dissolve correctly but always predicts dissolve for grow
                mock_preds.append({
                    "model": "model_A",
                    "seed": 42,
                    "window": "final",
                    "community_id": f"c_{cid}",
                    "feature_month": f_month,
                    "label_month": m,
                    "reference_id": "ref_1",
                    "label_reference_id": "lref_1",
                    "y_true": "dissolve" if cid < 8 else "grow",
                    "y_pred": "dissolve" if cid < 8 else "grow",
                    "fallback": 0,
                    "probabilities": json.dumps([0.0]*5 + [1.0]),
                })
                mock_preds.append({
                    "model": "model_B",
                    "seed": 42,
                    "window": "final",
                    "community_id": f"c_{cid}",
                    "feature_month": f_month,
                    "label_month": m,
                    "reference_id": "ref_1",
                    "label_reference_id": "lref_1",
                    "y_true": "dissolve" if cid < 8 else "grow",
                    "y_pred": "dissolve",  # Always predicts dissolve
                    "fallback": 0,
                    "probabilities": json.dumps([0.0]*5 + [1.0]),
                })

        # Run paired block-bootstrap with block_length=2
        res2 = paired_block_bootstrap_comparison(
            mock_preds,
            proposed="model_A",
            reference="model_B",
            block_length=2,
            draws=100,
            seed=20261031,
        )
        self.assertEqual(res2["months"], 9)
        self.assertEqual(res2["draws"], 100)
        self.assertEqual(res2["block_length"], 2)
        self.assertGreater(res2["delta"], 0.0)  # Model A strictly better on grow
        self.assertIsNotNone(res2["low"])
        self.assertIsNotNone(res2["high"])
        self.assertLessEqual(res2["low"], res2["high"])

        # Identical models must produce exact delta=0.0 and [0.0, 0.0] interval
        res_ident = paired_block_bootstrap_comparison(
            mock_preds,
            proposed="model_A",
            reference="model_A",
            block_length=2,
            draws=50,
            seed=20261031,
        )
        self.assertEqual(res_ident["delta"], 0.0)
        self.assertEqual(res_ident["low"], 0.0)
        self.assertEqual(res_ident["high"], 0.0)

        # Under 6 months, must cleanly decline interval calculation
        short_preds = [r for r in mock_preds if r["label_month"] in months[:4]]
        res_short = paired_block_bootstrap_comparison(
            short_preds,
            proposed="model_A",
            reference="model_B",
            block_length=2,
            draws=50,
        )
        self.assertIsNone(res_short["low"])
        self.assertIsNone(res_short["high"])
        self.assertEqual(res_short["reason"], "Fewer than six distinct months")

    def test_paired_alignment_check(self):
        """Test paired model alignment verification and error detection on key/label mismatch."""
        # 1. Calibrated fixture must pass alignment check
        audit = validate_paired_alignment(
            self.calibrated_preds,
            proposed="hier_lr_dynamic",
            reference="hier_hgb_dynamic",
        )
        self.assertEqual(audit["status"], "PASS")
        self.assertIn(42, audit["seeds"])
        self.assertEqual(audit["aligned_cases_per_seed"][42], 1269)

        # 2. Corrupted fixture: missing key in reference must raise ValueError
        corrupt_preds = [dict(r) for r in self.calibrated_preds]
        hgb_idx = next(i for i, r in enumerate(corrupt_preds) if r["model"] == "hier_hgb_dynamic")
        del corrupt_preds[hgb_idx]

        with self.assertRaises(ValueError):
            validate_paired_alignment(corrupt_preds, "hier_lr_dynamic", "hier_hgb_dynamic")

        # 3. Corrupted fixture: label disagreement must raise ValueError
        corrupt_label_preds = [dict(r) for r in self.calibrated_preds]
        hgb_row = next(r for r in corrupt_label_preds if r["model"] == "hier_hgb_dynamic")
        hgb_row["y_true"] = "stable" if hgb_row["y_true"] != "stable" else "dissolve"

        with self.assertRaises(ValueError):
            validate_paired_alignment(corrupt_label_preds, "hier_lr_dynamic", "hier_hgb_dynamic")

    def test_real_full_study_reproduction(self):
        """Test exact reproduction of full-study delta and 95% CI on real frozen handoff."""
        if not self.handoff_p.exists():
            self.skipTest("Real handoff file predictions_final.csv not present.")

        df = pd.read_csv(self.handoff_p, low_memory=False)
        sub = df[df["model"].isin(["hier_lr_dynamic", "hier_hgb_dynamic"])].to_dict("records")

        # 1. Alignment check must PASS
        audit = validate_paired_alignment(sub, "hier_lr_dynamic", "hier_hgb_dynamic")
        self.assertEqual(audit["status"], "PASS")
        for s in (42, 43, 44):
            self.assertEqual(audit["aligned_cases_per_seed"][s], 1269)

        # 2. Point difference delta must match 0.023692
        res2 = paired_block_bootstrap_comparison(
            sub,
            proposed="hier_lr_dynamic",
            reference="hier_hgb_dynamic",
            block_length=2,
            draws=2000,
            seed=20261031,
        )
        self.assertAlmostEqual(res2["delta"], 0.023692, places=5)
        # Check 95% CI matches lr_hgb_cross_cohort_intervals.csv within 1e-4
        self.assertAlmostEqual(res2["low"], -0.069913, places=4)
        self.assertAlmostEqual(res2["high"], 0.099322, places=4)

        # 3. Block length 3 matches [-0.0828, 0.0984]
        res3 = paired_block_bootstrap_comparison(
            sub,
            proposed="hier_lr_dynamic",
            reference="hier_hgb_dynamic",
            block_length=3,
            draws=2000,
            seed=20261031,
        )
        self.assertAlmostEqual(res3["low"], -0.082800, places=4)
        self.assertAlmostEqual(res3["high"], 0.098384, places=4)


if __name__ == "__main__":
    unittest.main()
