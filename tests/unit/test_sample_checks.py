"""Unit tests for prediction sample validation."""

import unittest
from pathlib import Path

import pandas as pd

from reddit_sna.benchmarks.community_table import feature_catalog, read_table
from reddit_sna.evaluation.splits import assign_temporal_split
from reddit_sna.evaluation.sample_checks import (
    SampleCheckError,
    assert_samples_ok,
    check_samples,
)


FIXTURE = Path("tests/fixtures/prediction/samples_mini.csv")


class TestSampleChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = read_table(FIXTURE)
        cls.catalog = feature_catalog()
        cls.split = assign_temporal_split(cls.samples)

    def report(self, samples=None, catalog=None, split=None):
        return check_samples(
            self.samples if samples is None else samples,
            self.catalog if catalog is None else catalog,
            self.split if split is None else split,
        )

    def failed_checks(self, report):
        return report.loc[report["status"] == "FAIL", "check"].tolist()

    def test_valid_fixture_has_no_failures(self):
        report = self.report()
        self.assertEqual(
            list(report.columns),
            ["check", "status", "detail"],
        )
        self.assertFalse((report["status"] == "FAIL").any(), report.to_string())

    def test_assert_accepts_valid_report(self):
        assert_samples_ok(self.report())

    def test_detects_duplicate_sample_keys(self):
        samples = pd.concat(
            [self.samples, self.samples.iloc[[0]]],
            ignore_index=True,
        )

        self.assertIn("unique_sample_keys", self.failed_checks(self.report(samples)))

    def test_detects_invalid_label(self):
        samples = self.samples.copy()
        samples.loc[samples.index[0], "label"] = "unknown_event"

        self.assertIn("labels_valid", self.failed_checks(self.report(samples)))

    def test_detects_inconsistent_label_month(self):
        samples = self.samples.copy()
        samples.loc[samples.index[0], "label_month"] = "2015-12"

        self.assertIn(
            "label_month_follows_feature_month",
            self.failed_checks(self.report(samples)),
        )

    def test_assert_raises_for_invalid_report(self):
        samples = self.samples.copy()
        samples.loc[samples.index[0], "label"] = "unknown_event"

        with self.assertRaisesRegex(SampleCheckError, "Invalid prediction samples"):
            assert_samples_ok(self.report(samples))

    def test_detects_missing_required_column(self):
        samples = self.samples.drop(columns=["community_id"])

        self.assertIn("required_columns", self.failed_checks(self.report(samples)))

    def test_detects_non_numeric_value(self):
        samples = self.samples.copy()
        samples["density"] = samples["density"].astype(object)
        samples.loc[samples.index[0], "density"] = "invalid"

        self.assertIn("numeric_values_finite", self.failed_checks(self.report(samples)))

    def test_detects_infinite_numeric_value(self):
        samples = self.samples.copy()
        samples.loc[samples.index[0], "density"] = float("inf")

        self.assertIn("numeric_values_finite", self.failed_checks(self.report(samples)))

    def test_detects_out_of_range_density(self):
        samples = self.samples.copy()
        samples.loc[samples.index[0], "density"] = 1.5

        self.assertIn("numeric_ranges_valid", self.failed_checks(self.report(samples)))

    def test_detects_unexpected_column(self):
        samples = self.samples.copy()
        samples["unexpected_feature"] = 123

        failed = self.failed_checks(self.report(samples))
        self.assertIn("features_in_catalog", failed)
        self.assertIn("no_unexpected_columns", failed)

    def test_detects_t_plus_1_feature_from_catalog(self):
        samples = self.samples.copy()
        samples["future_feature"] = 1.0
        catalog = pd.concat(
            [
                self.catalog,
                pd.DataFrame([{
                    "feature": "future_feature",
                    "dtype": "float64",
                    "source": "test",
                    "window": "t+1",
                    "available_at": "t+1",
                    "allowed_models": "none",
                    "note": "Intentional leakage test",
                }]),
            ],
            ignore_index=True,
        )

        failed = self.failed_checks(self.report(samples, catalog=catalog))
        self.assertIn("no_t_plus_1_features", failed)

    def test_detects_single_class_in_train(self):
        split = self.split.copy()
        train_keys = split["split"] == "train"
        train_ids = set(split.loc[train_keys, "reference_id"])
        train_months = set(split.loc[train_keys, "label_month"])

        samples = self.samples.copy()
        mask = (
            samples["reference_id"].isin(train_ids)
            & samples["label_month"].isin(train_months)
        )
        train_rows = samples.loc[mask]
        if len(train_rows) >= 2:
            samples.loc[train_rows.index, "label"] = "stable"

        report = self.report(samples, split=split)
        self.assertIn("train_class_support", self.failed_checks(report))

    def test_leaky_fixture_is_detected(self):
        leaky_path = Path("tests/fixtures/prediction/samples_leaky.csv")
        leaky_samples = pd.read_csv(
            leaky_path,
            dtype={
                "reference_id": str,
                "feature_month": str,
                "community_id": str,
                "label_month": str,
                "label": str,
                "prev_label": str,
            },
        )

        leaky_catalog = pd.concat(
            [
                self.catalog,
                pd.DataFrame([{
                    "feature": "future_feature",
                    "dtype": "float64",
                    "source": "test",
                    "window": "t+1",
                    "available_at": "t+1",
                    "allowed_models": "none",
                    "note": "Intentional leakage test",
                }]),
            ],
            ignore_index=True,
        )

        report = check_samples(leaky_samples, leaky_catalog)
        failed = self.failed_checks(report)

        self.assertIn("no_t_plus_1_features", failed)

if __name__ == "__main__":
    unittest.main()
