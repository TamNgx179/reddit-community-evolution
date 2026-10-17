"""Unit tests for models/logistic_regression.py."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from reddit_sna.contracts import Event
from reddit_sna.models.logistic_regression import (
    B4Config,
    B4_FEATURES,
    fit_logreg,
    predict_logreg,
    save_config,
)
from reddit_sna.models.majority_persistence import fit_majority


def _make_train(n_per_class: int = 20, seed: int = 0) -> pd.DataFrame:
    """Generate train data with all 6 classes and all B4 features."""
    rng = np.random.default_rng(seed)
    rows = []
    for i, event in enumerate(Event):
        for j in range(n_per_class):
            base_size = 10 + i * 5 + j
            rows.append({
                "reference_id": "r",
                "feature_month": "2015-02",
                "community_id": f"c{i*n_per_class+j:04d}",
                "label_month": "2015-03",
                "label": event.value,
                "prev_label": "",
                "size_t": base_size,
                "size_tm1": max(3, base_size - 2),
                "size_tm2": max(3, base_size - 4),
                "age_months": j + 1,
                "growth_rate": float(rng.uniform(-0.3, 0.3)),
                "density": float(rng.uniform(0.1, 0.9)),
                "reciprocity": float(rng.uniform(0.1, 0.9)),
            })
    return pd.DataFrame(rows)


def _make_test(n: int = 10, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        rows.append({
            "reference_id": "r",
            "feature_month": "2017-01",
            "community_id": f"c{i:04d}",
            "label_month": "2017-02",
            "label": "stable",
            "prev_label": "",
            "size_t": int(rng.integers(5, 50)),
            "size_tm1": int(rng.integers(3, 40)),
            "size_tm2": int(rng.integers(3, 30)),
            "age_months": int(rng.integers(1, 20)),
            "growth_rate": float(rng.uniform(-0.3, 0.3)),
            "density": float(rng.uniform(0.1, 0.9)),
            "reciprocity": float(rng.uniform(0.1, 0.9)),
        })
    return pd.DataFrame(rows)


class TestFitLogreg(unittest.TestCase):

    def setUp(self):
        self.train = _make_train()
        self.model = fit_logreg(self.train, seed=42)

    def test_scaler_mean_matches_train_mean(self):
        feat_vals = self.train[self.train["label"] != ""][list(B4_FEATURES)].dropna().astype(float)
        expected_mean = feat_vals.mean().values
        np.testing.assert_allclose(self.model.scaler.mean_, expected_mean, rtol=1e-4)

    def test_train_one_class_raises(self):
        train_1class = _make_train()
        train_1class["label"] = "stable"
        with self.assertRaises(ValueError):
            fit_logreg(train_1class, seed=42)

    def test_same_seed_same_predictions(self):
        m1 = fit_logreg(self.train, seed=7)
        m2 = fit_logreg(self.train, seed=7)
        test = _make_test()
        p1 = predict_logreg(m1, test)
        p2 = predict_logreg(m2, test)
        pd.testing.assert_frame_equal(p1, p2)

    def test_different_test_labels_do_not_change_model_coefficients(self):
        """Changing test labels must not change fitted scaler or coefficients."""
        test1 = _make_test()
        test2 = test1.copy()
        test2["label"] = "dissolve"
        m1 = fit_logreg(self.train, seed=42)
        # Predict on both test sets
        p1 = predict_logreg(m1, test1)
        p2 = predict_logreg(m1, test2)
        # y_pred should be identical (model doesn't read test label)
        pd.testing.assert_series_equal(p1["y_pred"], p2["y_pred"], check_names=False)

    def test_probas_sum_to_one(self):
        test = _make_test()
        preds = predict_logreg(self.model, test)
        proba_cols = [f"proba_{e.value}" for e in Event]
        for _, row in preds.iterrows():
            total = sum(row[c] for c in proba_cols if row[c] is not None)
            self.assertAlmostEqual(total, 1.0, places=5)

    def test_fallback_rows_with_missing_features(self):
        test = _make_test()
        # Introduce NaN in a B4 feature
        test.loc[test.index[0], "size_t"] = None
        preds = predict_logreg(self.model, test)
        self.assertTrue(preds.iloc[0]["used_fallback"])
        # Others should not fallback
        self.assertFalse(preds.iloc[1]["used_fallback"])

    def test_predict_does_not_read_label_column(self):
        """Predict result unchanged whether test label is stable or dissolve."""
        test = _make_test()
        original_preds = predict_logreg(self.model, test)
        test["label"] = "dissolve"
        modified_preds = predict_logreg(self.model, test)
        pd.testing.assert_series_equal(
            original_preds["y_pred"], modified_preds["y_pred"], check_names=False
        )

    def test_missing_train_classes_recorded(self):
        """If a class is missing in train, it should appear in missing_train_classes."""
        train_no_dissolve = _make_train()
        train_no_dissolve = train_no_dissolve[train_no_dissolve["label"] != "dissolve"]
        model = fit_logreg(train_no_dissolve, seed=42)
        self.assertIn("dissolve", model.missing_train_classes)

    def test_save_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = save_config(B4Config(), self.model, Path(tmp))
            self.assertTrue(path.exists())
            import json
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["model"], "B4_logreg")
            self.assertEqual(data["features"], list(B4_FEATURES))


if __name__ == "__main__":
    unittest.main()