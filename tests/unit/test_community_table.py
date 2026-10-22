"""Unit tests for benchmarks/community_table.py.

Tests: determinism, schema, key uniqueness, label validity, growth_rate
consistency, round-trip contract (SampleKey + CommunitySample), all 6 events
in train range, no unexpected columns, and history-consistency regressions
(size_tm1 / size_tm2 / prev_label / age_months).
"""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from reddit_sna.benchmarks.community_table import (
    SAMPLE_COLUMNS,
    FEATURE_COLS,
    feature_catalog,
    generate_community_table,
    read_table,
    write_table,
    csv_sha256,
)
from reddit_sna.contracts import CommunitySample, Event, SampleKey, next_month


class TestGenerateCommunityTable(unittest.TestCase):

    def setUp(self):
        self.seed = 42
        self.df = generate_community_table(self.seed)

    def test_determinism_same_seed(self):
        """Same seed -> identical table."""
        df2 = generate_community_table(self.seed)
        pd.testing.assert_frame_equal(self.df, df2, check_like=False)

    def test_different_seed_different_table(self):
        """Different seed -> different table."""
        df_other = generate_community_table(self.seed + 1)
        self.assertFalse(
            self.df["label"].equals(df_other["label"]),
            "Different seeds produced identical label columns",
        )

    def test_exactly_14_columns(self):
        self.assertEqual(list(self.df.columns), list(SAMPLE_COLUMNS))

    def test_key_uniqueness(self):
        keys = self.df[["reference_id", "feature_month", "community_id"]]
        self.assertEqual(len(keys), len(keys.drop_duplicates()))

    def test_label_month_is_next_month(self):
        for _, row in self.df.iterrows():
            self.assertEqual(
                row["label_month"],
                next_month(row["feature_month"]),
                f"label_month mismatch at {row['feature_month']}",
            )

    def test_label_valid_or_empty_last_month(self):
        valid_events = {e.value for e in Event}
        last_feature = self.df["feature_month"].max()
        for _, row in self.df.iterrows():
            if row["feature_month"] == last_feature:
                self.assertEqual(row["label"], "", "Last feature month should have empty label")
            else:
                self.assertIn(
                    row["label"],
                    valid_events,
                    f"Invalid label '{row['label']}' at {row['feature_month']}",
                )

    def test_growth_rate_computed_from_sizes(self):
        """growth_rate == (size_t - size_tm1) / size_tm1 where size_tm1 is not null."""
        has_tm1 = self.df[self.df["size_tm1"].notna() & (self.df["size_tm1"] != 0)]
        self.assertGreater(len(has_tm1), 0)
        for _, row in has_tm1.iterrows():
            expected = (int(row["size_t"]) - int(row["size_tm1"])) / int(row["size_tm1"])
            actual = float(row["growth_rate"])
            self.assertAlmostEqual(
                actual, expected, places=6,
                msg=f"growth_rate mismatch at {row['feature_month']}",
            )

    def test_no_extra_columns_outside_catalog(self):
        cat = feature_catalog()
        catalog_features = set(cat["feature"].tolist())
        non_feature = {"reference_id", "feature_month", "community_id",
                       "label_month", "label"}
        allowed = catalog_features | non_feature
        for col in self.df.columns:
            self.assertIn(col, allowed, f"Unexpected column: {col}")

    def test_all_six_events_in_train(self):
        """All 6 Event classes present >= 15 times in default train range."""
        train_mask = (
            (self.df["label_month"] >= "2015-02")
            & (self.df["label_month"] <= "2016-12")
            & (self.df["label"] != "")
        )
        train_labels = self.df.loc[train_mask, "label"]
        for event in Event:
            count = (train_labels == event.value).sum()
            self.assertGreaterEqual(
                count, 15,
                f"Class '{event.value}' has {count} train samples (need >= 15)",
            )

    def test_round_trip_contract(self):
        """Every labelled row can construct SampleKey + CommunitySample without error."""
        labelled = self.df[self.df["label"] != ""]
        for _, row in labelled.iterrows():
            key = SampleKey(
                reference_id=str(row["reference_id"]),
                feature_month=str(row["feature_month"]),
                community_id=str(row["community_id"]),
            )
            features = {
                col: (None if pd.isna(row[col]) else float(row[col]))
                for col in FEATURE_COLS
            }
            cs = CommunitySample(
                key=key,
                label_month=str(row["label_month"]),
                label=Event(str(row["label"])),
                features=features,
            )
            self.assertEqual(cs.key, key)

    def test_write_and_read_table_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = feature_catalog()
            paths = write_table(self.df, catalog, Path(tmpdir))
            df2 = read_table(paths["samples.csv"])
            # pandas 3 uses a string dtype, pandas 2 uses object
            self.assertTrue(
                str(df2["community_id"].dtype) in ("object", "string", "str"),
                f"community_id dtype should be string-like, got: {df2['community_id'].dtype}",
            )
            for col in ("size_t", "age_months"):
                self.assertEqual(str(df2[col].dtype), "Int64", f"{col} should be Int64")
            self.assertEqual(len(df2), len(self.df))

    def test_csv_sha256_same_seed(self):
        with tempfile.TemporaryDirectory() as tmpdir1, \
             tempfile.TemporaryDirectory() as tmpdir2:
            cat = feature_catalog()
            p1 = write_table(generate_community_table(99), cat, Path(tmpdir1))
            p2 = write_table(generate_community_table(99), cat, Path(tmpdir2))
            self.assertEqual(
                csv_sha256(p1["samples.csv"]),
                csv_sha256(p2["samples.csv"]),
            )

    # ------------------------------------------------------------------
    # Regression tests for the "stale history" bug (size_tm1 == size_t)
    # ------------------------------------------------------------------

    def test_size_tm1_follows_prev_label(self):
        """prev_label is the event applied between t-1 and t, so sizes must obey it.

          grow                  -> size_t  >  size_tm1  (grow always adds >= 1 member)
          shrink / merge / split -> size_t <= size_tm1
          stable                -> size_t ==  size_tm1

        If size_tm1 were assigned AFTER the size update, size_tm1 == size_t on
        every row and the 'grow' assertion below fails.
        """
        d = self.df[self.df["size_tm1"].notna()].copy()
        d["size_t"] = d["size_t"].astype(int)
        d["size_tm1"] = d["size_tm1"].astype(int)

        grown = d[d["prev_label"] == "grow"]
        self.assertGreater(len(grown), 20, "Too few 'grow' rows to test")
        self.assertTrue((grown["size_t"] > grown["size_tm1"]).all(),
                        "Rows with prev_label=grow must have size_t > size_tm1")

        down = d[d["prev_label"].isin(["shrink", "merge", "split"])]
        self.assertGreater(len(down), 20, "Too few shrink/merge/split rows to test")
        self.assertTrue((down["size_t"] <= down["size_tm1"]).all(),
                        "Rows with prev_label in shrink/merge/split must have size_t <= size_tm1")

        stable = d[d["prev_label"] == "stable"]
        self.assertGreater(len(stable), 20, "Too few 'stable' rows to test")
        self.assertTrue((stable["size_t"] == stable["size_tm1"]).all(),
                        "Rows with prev_label=stable must have size_t == size_tm1")

    def test_growth_rate_not_uniformly_zero(self):
        """If size_tm1 == size_t (stale history), growth_rate would be 0 everywhere."""
        valid_gr = self.df["growth_rate"].dropna()
        self.assertGreater(len(valid_gr), 0, "No rows have growth_rate defined")
        std = float(valid_gr.std())
        self.assertGreater(
            std, 0.05,
            f"growth_rate std={std:.4f} is suspiciously low (stale size_tm1?)",
        )

    def test_history_columns_match_age(self):
        """age 0 -> no history; age 1 -> size_tm1 only; age >= 2 -> both; prev_label empty iff age 0."""
        age = self.df["age_months"].astype(int)
        a0 = self.df[age == 0]
        a1 = self.df[age == 1]
        a2 = self.df[age >= 2]
        self.assertGreater(len(a0), 0)
        self.assertGreater(len(a1), 0)
        self.assertGreater(len(a2), 0)
        self.assertTrue(a0["size_tm1"].isna().all() and a0["size_tm2"].isna().all())
        self.assertTrue(a1["size_tm1"].notna().all() and a1["size_tm2"].isna().all())
        self.assertTrue(a2["size_tm1"].notna().all() and a2["size_tm2"].notna().all())
        self.assertTrue(((self.df["prev_label"] == "") == (age == 0)).all())

    def test_community_ids_are_local_per_month(self):
        """No lineage: the first month's ids are c0000..c{n-1}, and a month's ids are unique."""
        first = self.df[self.df["feature_month"] == self.df["feature_month"].min()]
        n = len(first)
        self.assertEqual(set(first["community_id"]), {f"c{i:04d}" for i in range(n)})


class TestFeatureCatalog(unittest.TestCase):

    def test_catalog_columns(self):
        cat = feature_catalog()
        expected_cols = ["feature", "dtype", "source", "window",
                         "available_at", "allowed_models", "note"]
        self.assertEqual(list(cat.columns), expected_cols)

    def test_no_future_available_at(self):
        cat = feature_catalog()
        for _, row in cat.iterrows():
            self.assertNotEqual(row["available_at"], "t+1",
                                f"Feature '{row['feature']}' has available_at='t+1'")

    def test_feature_columns_subset_of_table(self):
        cat = feature_catalog()
        table_cols = set(SAMPLE_COLUMNS)
        for feat in cat["feature"]:
            self.assertIn(feat, table_cols, f"Catalog feature '{feat}' not in table columns")

    def test_allowed_models_values(self):
        cat = feature_catalog()
        allowed = {"B1_persistence", "B4_logreg", "reserved"}
        for _, row in cat.iterrows():
            self.assertIn(row["allowed_models"], allowed,
                          f"Unexpected allowed_models: {row['allowed_models']}")


if __name__ == "__main__":
    unittest.main()