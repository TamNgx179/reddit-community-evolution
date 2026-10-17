"""Checks that tests/fixtures/prediction/samples_mini.csv is a valid slice of the generator.

Anh uses this fixture to test assign_temporal_split / sample checks / metrics, so it must
(1) follow the 14-column schema, (2) cover train, validation AND test, (3) contain all
6 classes, rows without history and rows without label, and (4) be real generator output.
If test (4) fails, regenerate with tests/fixtures/prediction/make_samples_mini.py.
"""
import unittest
from pathlib import Path

import numpy as np

from reddit_sna.benchmarks.community_table import (
    SAMPLE_COLUMNS,
    generate_community_table,
    read_table,
)
from reddit_sna.contracts import Event, next_month

_REL = Path("tests") / "fixtures" / "prediction" / "samples_mini.csv"


def _find_fixture() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / _REL
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Cannot find {_REL} above {__file__}")


class TestSamplesMiniFixture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.path = _find_fixture()
        cls.df = read_table(cls.path)

    def test_schema_and_size(self):
        self.assertEqual(list(self.df.columns), list(SAMPLE_COLUMNS))
        self.assertTrue(40 <= len(self.df) <= 120, f"unexpected size {len(self.df)}")

    def test_keys_unique_and_label_month(self):
        keys = self.df[["reference_id", "feature_month", "community_id"]]
        self.assertEqual(len(keys), len(keys.drop_duplicates()))
        for _, row in self.df.iterrows():
            self.assertEqual(row["label_month"], next_month(row["feature_month"]))

    def test_all_six_classes_present(self):
        present = set(self.df["label"]) - {""}
        self.assertEqual(present, {e.value for e in Event})

    def test_covers_train_validation_and_test(self):
        labelled = self.df[self.df["label"] != ""]
        lm = labelled["label_month"]
        n_train = ((lm >= "2015-02") & (lm <= "2016-12")).sum()
        n_val = ((lm >= "2017-01") & (lm <= "2017-06")).sum()
        n_test = ((lm >= "2017-07") & (lm <= "2017-12")).sum()
        self.assertGreater(n_train, 0)
        self.assertGreater(n_val, 0)
        self.assertGreater(n_test, 0)

    def test_has_rows_without_history_and_without_label(self):
        self.assertTrue(self.df["size_tm1"].isna().any(), "need rows with missing history")
        self.assertTrue((self.df["label"] == "").any(), "need rows with empty label")
        empty = self.df[self.df["label"] == ""]
        self.assertTrue((empty["feature_month"] == "2017-12").all())

    def test_rows_are_real_generator_output(self):
        full = generate_community_table(42).set_index(
            ["reference_id", "feature_month", "community_id"])
        for _, row in self.df.iterrows():
            key = (row["reference_id"], row["feature_month"], row["community_id"])
            self.assertIn(key, full.index, f"{key} not produced by generator(42)")
            ref = full.loc[key]
            for col in ("label_month", "label", "prev_label"):
                self.assertEqual(row[col], ref[col], f"{col} differs at {key}")
            for col in ("size_t", "size_tm1", "size_tm2", "age_months"):
                a, b = row[col], ref[col]
                self.assertTrue((a is None or str(a) == "<NA>") == (b is None or str(b) == "<NA>"))
                if str(a) != "<NA>":
                    self.assertEqual(int(a), int(b), f"{col} differs at {key}")
            for col in ("growth_rate", "retention_prev", "density", "reciprocity"):
                a, b = float(row[col]), float(ref[col])
                self.assertTrue((np.isnan(a) and np.isnan(b)) or abs(a - b) < 1e-9,
                                f"{col} differs at {key}")


if __name__ == "__main__":
    unittest.main()