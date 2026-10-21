"""Tests for the split-aware leakage checks added to evaluation/sample_checks.py."""
import unittest

import numpy as np
import pandas as pd

from reddit_sna.benchmarks.community_table import feature_catalog, generate_community_table
from reddit_sna.evaluation.sample_checks import (
    SampleCheckError,
    assert_samples_ok,
    check_samples,
)

KEYS = ["reference_id", "feature_month", "community_id", "label_month"]


def _make_split(samples: pd.DataFrame) -> pd.DataFrame:
    labelled = samples[samples["label"] != ""]
    lm = labelled["label_month"]
    split = labelled[KEYS].copy()
    split["split"] = np.where(
        lm <= "2016-12", "train", np.where(lm <= "2017-06", "validation", "test")
    )
    return split.reset_index(drop=True)


def _status(report: pd.DataFrame, check: str) -> str:
    rows = report.loc[report["check"] == check, "status"]
    assert len(rows) == 1, f"check {check!r} appears {len(rows)} times"
    return rows.iloc[0]


class TestSplitIntegrityChecks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.samples = generate_community_table(42)
        cls.catalog = feature_catalog()
        cls.split = _make_split(cls.samples)

    def test_valid_split_passes_everything(self):
        report = check_samples(self.samples, self.catalog, self.split)
        self.assertTrue((report["status"] == "PASS").all(), report.to_string())
        assert_samples_ok(report)  # must not raise

    def test_new_checks_present_only_with_split(self):
        without = check_samples(self.samples, self.catalog)
        self.assertNotIn("temporal_order_no_overlap", set(without["check"]))
        with_split = check_samples(self.samples, self.catalog, self.split)
        for name in ("split_values_valid", "split_keys_are_labelled_samples",
                     "temporal_order_no_overlap", "catalog_available_at_valid"):
            self.assertIn(name, set(with_split["check"]))

    def test_invalid_split_name_fails(self):
        split = self.split.copy()
        split.loc[0, "split"] = "dev"
        report = check_samples(self.samples, self.catalog, split)
        self.assertEqual(_status(report, "split_values_valid"), "FAIL")
        with self.assertRaises(SampleCheckError):
            assert_samples_ok(report)

    def test_split_key_not_in_samples_fails(self):
        split = self.split.copy()
        phantom = split.iloc[[0]].copy()
        phantom["community_id"] = "c9999"
        split = pd.concat([split, phantom], ignore_index=True)
        report = check_samples(self.samples, self.catalog, split)
        self.assertEqual(_status(report, "split_keys_are_labelled_samples"), "FAIL")

    def test_split_key_pointing_to_unlabelled_row_fails(self):
        unlabelled = self.samples[self.samples["label"] == ""].iloc[[0]]
        extra = unlabelled[KEYS].copy()
        extra["split"] = "test"
        split = pd.concat([self.split, extra], ignore_index=True)
        report = check_samples(self.samples, self.catalog, split)
        self.assertEqual(_status(report, "split_keys_are_labelled_samples"), "FAIL")

    def test_temporal_overlap_fails(self):
        split = self.split.copy()
        # Put one validation row (label_month in 2017-01..2017-06) into train:
        # train would then extend past the start of validation.
        idx = split.index[split["split"] == "validation"][0]
        split.loc[idx, "split"] = "train"
        report = check_samples(self.samples, self.catalog, split)
        self.assertEqual(_status(report, "temporal_order_no_overlap"), "FAIL")

    def test_future_available_at_variants_fail(self):
        # The old check only looked for the exact string "t+1"; "t+2" slipped through.
        catalog = self.catalog.copy()
        catalog.loc[catalog["feature"] == "size_t", "available_at"] = "t+2"
        report = check_samples(self.samples, catalog, self.split)
        self.assertEqual(_status(report, "no_t_plus_1_features"), "PASS")  # old hole
        self.assertEqual(_status(report, "catalog_available_at_valid"), "FAIL")

    def test_past_available_at_is_allowed(self):
        catalog = self.catalog.copy()
        catalog.loc[catalog["feature"] == "size_t", "available_at"] = "t-1"
        report = check_samples(self.samples, catalog, self.split)
        self.assertEqual(_status(report, "catalog_available_at_valid"), "PASS")


if __name__ == "__main__":
    unittest.main()