"""Causal selection and finite fit budget without an estimator dependency."""

import unittest

import numpy as np

from reddit_sna.models.hetco import EVENTS
from reddit_sna.pipelines.hetco_threshold import select_threshold


class ThresholdSelectionTests(unittest.TestCase):
    def test_selection_excludes_later_labels_and_reuses_each_fit_for_grid(self):
        samples = [dict(label_month=m, label="dissolve")
                   for m in ("2015-06", "2015-07", "2015-08", "2015-10")]
        declaration = dict(selection_months=["2015-07", "2015-08"],
                           thresholds=["argmax", 0.3, 0.5, 0.7])
        calls = []

        def fit(family, config, train, test, seed):
            origin = test[0]["label_month"]
            self.assertTrue(all(r["label_month"] < origin for r in train))
            self.assertNotIn("2015-10", [r["label_month"] for r in train+test])
            calls.append((origin, seed))
            probabilities = np.full((len(test), len(EVENTS)), 0.02)
            probabilities[:, EVENTS.index("dissolve")] = 0.9
            return probabilities

        rows, selected = select_threshold(samples, declaration, "attention", [42, 43, 44], fit)
        self.assertEqual(len(calls), 6)  # Two origins times three seeds, independent of grid size.
        self.assertEqual(len(set(calls)), 6)
        self.assertEqual(len(rows), 4)
        self.assertEqual(selected, "argmax")  # All grid scores tie; retain declaration order.


if __name__ == "__main__":
    unittest.main()
