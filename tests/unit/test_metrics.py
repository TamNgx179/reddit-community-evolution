import unittest

import pandas as pd

from reddit_sna.contracts import Event
from reddit_sna.evaluation.metrics import (
    LABELS,
    confusion_matrices,
    evaluate_predictions,
)


KEYS = ["reference_id", "feature_month", "community_id", "label_month"]


class TestEvaluationMetrics(unittest.TestCase):
    def setUp(self):
        rows = [
            ("ref-1", "2016-11", "c1", "2016-12", "train"),
            ("ref-2", "2016-12", "c2", "2017-01", "train"),
            ("ref-3", "2017-05", "c3", "2017-06", "validation"),
            ("ref-4", "2017-06", "c4", "2017-07", "test"),
            ("ref-5", "2017-06", "c5", "2017-07", "test"),
            ("ref-6", "2017-06", "c6", "2017-07", "test"),
        ]
        self.split = pd.DataFrame(rows, columns=KEYS + ["split"])

        self.predictions = pd.DataFrame([
            {
                "reference_id": "ref-4",
                "feature_month": "2017-06",
                "community_id": "c4",
                "label_month": "2017-07",
                "model": "baseline",
                "y_true": "stable",
                "y_pred": "stable",
            },
            {
                "reference_id": "ref-5",
                "feature_month": "2017-06",
                "community_id": "c5",
                "label_month": "2017-07",
                "model": "baseline",
                "y_true": "grow",
                "y_pred": "stable",
            },
            {
                "reference_id": "ref-6",
                "feature_month": "2017-06",
                "community_id": "c6",
                "label_month": "2017-07",
                "model": "baseline",
                "y_true": "shrink",
                "y_pred": "shrink",
            },
        ])

    def test_labels_follow_event_order(self):
        self.assertEqual(LABELS, [event.value for event in Event])
        self.assertEqual(len(LABELS), 6)

    def test_metrics_return_required_columns(self):
        result = evaluate_predictions(self.predictions, self.split)

        self.assertEqual(
            list(result["metrics"].columns),
            [
                "model", "split", "n", "n_classes_present",
                "macro_f1", "macro_f1_six", "balanced_accuracy",
            ],
        )
        self.assertEqual(
            list(result["per_class"].columns),
            [
                "model", "split", "label", "precision",
                "recall", "f1", "support",
            ],
        )

    def test_metrics_use_test_split_and_present_class_macro_f1(self):
        result = evaluate_predictions(self.predictions, self.split)
        metrics = result["metrics"].iloc[0]

        self.assertEqual(metrics["model"], "baseline")
        self.assertEqual(metrics["split"], "test")
        self.assertEqual(metrics["n"], 3)
        self.assertEqual(metrics["n_classes_present"], 3)
        self.assertAlmostEqual(metrics["macro_f1"], (2 / 3 + 0 + 1) / 3)

    def test_per_class_contains_all_six_labels(self):
        result = evaluate_predictions(self.predictions, self.split)
        per_class = result["per_class"]

        self.assertEqual(len(per_class), 6)
        self.assertEqual(set(per_class["label"]), set(LABELS))
        absent = per_class.loc[~per_class["label"].isin(
            self.predictions["y_true"]
        )]
        self.assertTrue((absent["support"] == 0).all())

    def test_confusion_matrices_are_keyed_by_model_and_split(self):
        matrices = confusion_matrices(self.predictions, self.split)

        self.assertEqual(set(matrices), {("baseline", "test")})
        matrix = matrices[("baseline", "test")]
        self.assertEqual(matrix.shape, (6, 6))
        self.assertEqual(int(matrix.to_numpy().sum()), 3)

    def test_invalid_event_label_is_rejected(self):
        predictions = self.predictions.copy()
        predictions.loc[0, "y_pred"] = "unknown"

        with self.assertRaisesRegex(ValueError, "Invalid event labels"):
            evaluate_predictions(predictions, self.split)

    def test_duplicate_model_sample_is_rejected(self):
        predictions = pd.concat(
            [self.predictions, self.predictions.iloc[[0]]],
            ignore_index=True,
        )

        with self.assertRaisesRegex(ValueError, "duplicate"):
            evaluate_predictions(predictions, self.split)

    def test_prediction_key_missing_from_split_is_rejected(self):
        predictions = self.predictions.copy()
        predictions.loc[0, "reference_id"] = "unknown-ref"

        with self.assertRaises(ValueError):
            evaluate_predictions(predictions, self.split)

    def test_empty_predictions_are_rejected(self):
        empty = self.predictions.iloc[0:0]

        with self.assertRaisesRegex(ValueError, "must not be empty"):
            evaluate_predictions(empty, self.split)


if __name__ == "__main__":
    unittest.main()