"""Unit tests for models/majority_persistence.py."""
import unittest

import pandas as pd

from reddit_sna.contracts import Event
from reddit_sna.models.majority_persistence import (
    MajorityModel,
    fit_majority,
    predict_majority,
    predict_persistence,
)


def _make_train(counts: dict[str, int]) -> pd.DataFrame:
    """Build a minimal DataFrame with the given label counts."""
    rows = []
    for label, n in counts.items():
        for _ in range(n):
            rows.append({"label": label, "reference_id": "r", "feature_month": "2015-02",
                         "community_id": "c0000", "prev_label": ""})
    return pd.DataFrame(rows)


def _make_samples(prev_labels: list[str]) -> pd.DataFrame:
    rows = []
    for i, pl in enumerate(prev_labels):
        rows.append({
            "reference_id": "r",
            "feature_month": "2015-03",
            "community_id": f"c{i:04d}",
            "label": "stable",
            "prev_label": pl,
        })
    return pd.DataFrame(rows)


class TestFitMajority(unittest.TestCase):

    def test_majority_is_most_frequent(self):
        train = _make_train({"stable": 10, "grow": 3, "dissolve": 2,
                             "shrink": 1, "merge": 1, "split": 1})
        model = fit_majority(train)
        self.assertEqual(model.majority_class, Event.STABLE)

    def test_tie_broken_by_event_order(self):
        # stable and grow tied at 5 each; stable comes first in Event
        train = _make_train({"stable": 5, "grow": 5, "dissolve": 1,
                             "shrink": 1, "merge": 1, "split": 1})
        model = fit_majority(train)
        self.assertEqual(model.majority_class, Event.STABLE)

    def test_grow_wins_tie_if_stable_absent(self):
        # Only grow and shrink, equal -> grow comes earlier in Event than shrink
        train = _make_train({"grow": 5, "shrink": 5})
        model = fit_majority(train)
        self.assertEqual(model.majority_class, Event.GROW)

    def test_empty_train_raises(self):
        empty = pd.DataFrame(columns=["label"])
        with self.assertRaises(ValueError):
            fit_majority(empty)

    def test_labelled_only_in_train(self):
        """Rows with empty label must be excluded."""
        rows = [
            {"label": "stable", "reference_id": "r", "feature_month": "2015-01",
             "community_id": "c0000", "prev_label": ""},
            {"label": "", "reference_id": "r", "feature_month": "2015-01",
             "community_id": "c0001", "prev_label": ""},
        ]
        train = pd.DataFrame(rows)
        model = fit_majority(train)
        self.assertEqual(model.majority_class, Event.STABLE)


class TestPredictMajority(unittest.TestCase):

    def setUp(self):
        self.model = fit_majority(_make_train({"grow": 10, "stable": 1}))

    def test_all_predict_majority_class(self):
        samples = _make_samples(["stable", "", "grow"])
        preds = predict_majority(self.model, samples)
        self.assertTrue((preds["y_pred"] == "grow").all())
        self.assertTrue((preds["used_fallback"] == False).all())

    def test_changing_test_labels_does_not_change_prediction(self):
        """Predictions must not read test labels."""
        s1 = _make_samples(["stable", "grow"])
        s2 = s1.copy()
        s2["label"] = "dissolve"
        p1 = predict_majority(self.model, s1)
        p2 = predict_majority(self.model, s2)
        pd.testing.assert_frame_equal(p1, p2)

    def test_empty_samples(self):
        preds = predict_majority(self.model, pd.DataFrame(
            columns=["reference_id", "feature_month", "community_id", "label", "prev_label"]
        ))
        self.assertEqual(len(preds), 0)


class TestPredictPersistence(unittest.TestCase):

    def setUp(self):
        self.model = fit_majority(_make_train({"stable": 10, "grow": 1, "dissolve": 1,
                                               "shrink": 1, "merge": 1, "split": 1}))

    def test_valid_prev_label_is_repeated(self):
        samples = _make_samples(["grow", "shrink", "merge"])
        preds = predict_persistence(self.model, samples)
        self.assertEqual(list(preds["y_pred"]), ["grow", "shrink", "merge"])
        self.assertTrue((preds["used_fallback"] == False).all())

    def test_missing_prev_label_falls_back_to_majority(self):
        samples = _make_samples(["", "stable"])
        preds = predict_persistence(self.model, samples)
        self.assertEqual(preds.iloc[0]["y_pred"], self.model.majority_class.value)
        self.assertTrue(preds.iloc[0]["used_fallback"])
        # valid prev_label -> no fallback
        self.assertFalse(preds.iloc[1]["used_fallback"])

    def test_fallback_flag_is_boolean(self):
        samples = _make_samples(["", "grow"])
        preds = predict_persistence(self.model, samples)
        for val in preds["used_fallback"]:
            self.assertIsInstance(val, bool)

    def test_train_only_one_class(self):
        """Majority can still be fit with one class; persistence should still work."""
        model = fit_majority(_make_train({"stable": 5}))
        samples = _make_samples(["grow", ""])
        preds = predict_persistence(model, samples)
        self.assertEqual(preds.iloc[0]["y_pred"], "grow")  # from prev_label
        self.assertEqual(preds.iloc[1]["y_pred"], "stable")  # fallback


if __name__ == "__main__":
    unittest.main()