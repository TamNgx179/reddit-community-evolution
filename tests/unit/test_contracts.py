import unittest

from reddit_sna.contracts import (
    CommunitySample, Event, Membership, Prediction, SampleKey, SnapshotEdge,
    TrackingLink, next_month,
)


class ContractTests(unittest.TestCase):
    def test_year_boundary_and_invalid_months(self):
        self.assertEqual(next_month("2015-12"), "2016-01")
        for month in ("2015-13", "2015-00", "15-01", "2015-1", "2015-01-01"):
            with self.subTest(month=month), self.assertRaises(ValueError):
                next_month(month)

    def test_edges_reject_self_loops_and_nonpositive_nonfinite_weights(self):
        self.assertEqual(SnapshotEdge("2015-01", "u1", "u2", 2).weight, 2)
        with self.assertRaises(ValueError):
            SnapshotEdge("2015-01", "u1", "u1", 1)
        for weight in (0, -1, float("nan"), float("inf")):
            with self.subTest(weight=weight), self.assertRaises(ValueError):
                SnapshotEdge("2015-01", "u1", "u2", weight)

    def test_membership_requires_identifiers(self):
        Membership("reference-v1", "2015-01", "c1", "u1")
        with self.assertRaises(ValueError):
            Membership("reference-v1", "2015-01", "", "u1")

    def test_tracking_requires_same_reference_and_next_month(self):
        source = SampleKey("jaccard-v1", "2015-12", "c1")
        TrackingLink(source, None)
        TrackingLink(source, SampleKey("jaccard-v1", "2016-01", "c9"))
        for target in (
            SampleKey("ged-v1", "2016-01", "c9"),
            SampleKey("jaccard-v1", "2016-02", "c9"),
        ):
            with self.subTest(target=target), self.assertRaises(ValueError):
                TrackingLink(source, target)

    def test_samples_and_predictions_label_the_following_month(self):
        key = SampleKey("reference-v1", "2015-12", "c1")
        CommunitySample(key, "2016-01", Event.GROW, {"size": 10.0})
        Prediction(key, "2016-01", "majority", Event.GROW, Event.STABLE)
        with self.assertRaises(ValueError):
            CommunitySample(key, "2015-12", Event.GROW, {})
        with self.assertRaises(ValueError):
            Prediction(key, "2016-02", "majority", Event.GROW, Event.STABLE)
        with self.assertRaises(ValueError):
            CommunitySample(key, "2016-01", "made-up-label", {})
