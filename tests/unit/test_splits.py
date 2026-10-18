import unittest

import pandas as pd

from reddit_sna.evaluation.splits import (
    assign_temporal_split,
    summarize_split,
)


class TemporalSplitTests(unittest.TestCase):
    def setUp(self):
        """Small dataset covering train, validation, test and unlabeled rows."""
        self.samples = pd.DataFrame(
            [
                {
                    "reference_id": "ref-1",
                    "feature_month": "2016-11",
                    "community_id": "c1",
                    "label_month": "2016-12",
                    "label": "stable",
                },
                {
                    "reference_id": "ref-2",
                    "feature_month": "2016-12",
                    "community_id": "c2",
                    "label_month": "2017-01",
                    "label": "grow",
                },
                {
                    "reference_id": "ref-3",
                    "feature_month": "2017-06",
                    "community_id": "c3",
                    "label_month": "2017-07",
                    "label": "shrink",
                },
                {
                    "reference_id": "ref-4",
                    "feature_month": "2017-12",
                    "community_id": "c4",
                    "label_month": "2018-01",
                    "label": "",
                },
            ]
        )

    def test_assign_temporal_split_uses_label_month(self):
        result = assign_temporal_split(self.samples)

        actual = dict(zip(result["reference_id"], result["split"]))

        self.assertEqual(
            actual,
            {
                "ref-1": "train",
                "ref-2": "validation",
                "ref-3": "test",
            },
        )

    def test_assign_temporal_split_drops_unlabeled_rows(self):
        result = assign_temporal_split(self.samples)

        self.assertEqual(len(result), 3)
        self.assertNotIn("ref-4", result["reference_id"].tolist())
        self.assertEqual(
            list(result.columns),
            [
                "reference_id",
                "feature_month",
                "community_id",
                "label_month",
                "split",
            ],
        )

    def test_summarize_split_counts_unlabeled_rows(self):
        split = assign_temporal_split(self.samples)
        summary = summarize_split(self.samples, split)

        dropped = summary.loc[
            summary["split"] == "unlabeled_dropped"
        ].iloc[0]

        self.assertEqual(dropped["n_samples"], 1)
        self.assertEqual(dropped["n_label_months"], 0)

        train = summary.loc[summary["split"] == "train"].iloc[0]
        validation = summary.loc[
            summary["split"] == "validation"
        ].iloc[0]
        test = summary.loc[summary["split"] == "test"].iloc[0]

        self.assertEqual(train["n_samples"], 1)
        self.assertEqual(validation["n_samples"], 1)
        self.assertEqual(test["n_samples"], 1)

    def test_assign_temporal_split_rejects_invalid_month(self):
        samples = pd.DataFrame(
            [
                {
                    "reference_id": "ref-1",
                    "feature_month": "2016-11",
                    "community_id": "c1",
                    "label_month": "2016-12",
                    "label": "stable",
                }
            ]
        )

        with self.assertRaises(ValueError):
            assign_temporal_split(samples, train_end="2017-13")

    def test_assign_temporal_split_rejects_wrong_boundary_order(self):
        with self.assertRaises(ValueError):
            assign_temporal_split(
                self.samples,
                train_end="2017-06",
                validation_end="2017-01",
            )

    def test_assign_temporal_split_rejects_empty_split(self):
        # Remove the only row that belongs to the test period.
        train_and_validation = self.samples.loc[
            self.samples["reference_id"].isin(
                ["ref-1", "ref-2", "ref-4"]
            )
        ].copy()

        with self.assertRaisesRegex(ValueError, "Empty split"):
            assign_temporal_split(train_and_validation)

    def test_assign_temporal_split_rejects_invalid_feature_month(self):
        samples = pd.DataFrame(
            [
                {
                    "reference_id": "ref-1",
                    "feature_month": "2016-13",
                    "community_id": "c1",
                    "label_month": "2017-01",
                    "label": "stable",
                }
            ]
        )

        with self.assertRaises(ValueError):
            assign_temporal_split(samples)

    def test_assign_temporal_split_rejects_inconsistent_label_month(self):
        samples = pd.DataFrame(
            [
                {
                    "reference_id": "ref-1",
                    "feature_month": "2016-11",
                    "community_id": "c1",
                    "label_month": "2017-01",
                    "label": "stable",
                }
            ]
        )

        with self.assertRaisesRegex(
            ValueError,
            "label_month must equal next_month",
        ):
            assign_temporal_split(samples)


if __name__ == "__main__":
    unittest.main()
