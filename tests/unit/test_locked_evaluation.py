import unittest

import numpy as np
import pandas as pd

from reddit_sna.evaluation.locked_metrics import (
    LABELS, evaluate_locked, validate_predictions, _f1_from_confusion,
)



class LockedEvaluationTests(unittest.TestCase):
    def fixture(self):
        rows = []
        truths = ["stable", "grow", "shrink", "merge", "split", "dissolve"]
        # A second month with only dissolve, intentionally absent five classes.
        month_specs = [("2020-01", truths), ("2020-02", ["dissolve", "dissolve"]),
                      ("2020-03", ["grow", "dissolve"]), ("2020-04", ["stable", "split"])]
        for cohort in ("cohort-A", "cohort-B"):
            for model in ("model-x", "model-y"):
                for seed in (1, 2):
                    for month, labels in month_specs:
                        for i, label in enumerate(labels):
                            pred = label
                            if model == "model-y" and label == "grow":
                                pred = "dissolve"
                            rows.append({"reference_id": f"{cohort}-ref", "feature_month": month,
                                        "community_id": f"{month}-{i}", "label_month": self.next_month(month),
                                        "label_reference_id": f"{cohort}-labels", "cohort": cohort,
                                        "model": model, "seed": seed, "y_true": label, "y_pred": pred})
        return pd.DataFrame(rows)

    @staticmethod
    def next_month(month):
        year, m = map(int, month.split("-"))
        m += 1
        if m > 12:
            year, m = year + 1, 1
        return f"{year:04d}-{m:02d}"


    def test_six_class_macro_f1_includes_absent_truth_classes_as_zero(self):
        cm = [[2, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0],
              [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]]
        macro, _, _, f1 = _f1_from_confusion(np.asarray(cm))
        self.assertAlmostEqual(macro, 1 / 6)
        self.assertEqual(len(f1), 6)

    def test_metrics_and_pairwise_bootstrap_are_complete_deterministic(self):
        data = self.fixture()
        results = evaluate_locked(data, draws=2000, block_length=3, seed=19)
        again = evaluate_locked(data, draws=2000, block_length=3, seed=19)
        self.assertEqual(set(results), {"overall", "monthly", "per_class_month", "confusion_month", "confusion_overall", "paired_bootstrap"})
        self.assertEqual(set(results["per_class_month"].label), set(LABELS))
        # Month-level class rows retain zero-support classes with support=0.
        absent = results["per_class_month"].query("label_month == '2020-03' and label == 'merge'")
        self.assertTrue((absent.support == 0).all())
        pd.testing.assert_frame_equal(results["paired_bootstrap"], again["paired_bootstrap"])
        pairs = results["paired_bootstrap"]
        self.assertEqual(len(pairs), 2)  # 2 cohorts × 1 pair
        self.assertTrue((pairs.status == "percentile_paired_block_bootstrap").all())
        self.assertTrue((pairs.block_length_months == 3).all())
        self.assertTrue((pairs.draws == 2000).all())

    def test_bootstrap_models_and_seeds_are_scoped_per_cohort(self):
        data = self.fixture()
        mask_b = data.cohort == "cohort-B"
        data.loc[mask_b & (data.model == "model-x"), "model"] = "model-z"
        data.loc[mask_b & (data.model == "model-y"), "model"] = "model-w"
        data.loc[mask_b, "seed"] = data.loc[mask_b, "seed"] + 10
        results = evaluate_locked(data, draws=25, block_length=3, seed=19)
        pairs = results["paired_bootstrap"]
        self.assertEqual(len(pairs), 2)
        self.assertEqual(set(zip(pairs.cohort, pairs.model_a, pairs.model_b)),
                         {("cohort-A", "model-x", "model-y"),
                          ("cohort-B", "model-w", "model-z")})
        self.assertTrue((pairs.status == "percentile_paired_block_bootstrap").all())

    def test_rejects_missing_model_sample_and_duplicate_rows(self):
        data = self.fixture()
        with self.assertRaisesRegex(ValueError, "incomplete or misaligned"):
            validate_predictions(data.drop(data.index[0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_predictions(pd.concat([data, data.iloc[[0]]], ignore_index=True))

    def test_unavailable_interval_when_month_count_less_than_block(self):
        data = self.fixture().query("label_month in ['2020-02', '2020-03']")
        results = evaluate_locked(data, draws=10, block_length=3, seed=2)
        self.assertTrue((results["paired_bootstrap"].status == "unavailable_insufficient_months").all())
        self.assertTrue(results["paired_bootstrap"].ci_low.isna().all())


if __name__ == "__main__":
    unittest.main()
