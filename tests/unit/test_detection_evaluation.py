"""Detection input alignment, before any AMI or coverage calculation."""

from dataclasses import replace
import unittest

from reddit_sna.contracts import Membership
from reddit_sna.evaluation.detection import align_memberships, count_snapshot


class DetectionAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.truth = [Membership("truth", "2020-01", group, user)
                      for group, user in (("B", "u02"), ("K", "isolated"), ("A", "u01"))]
        self.predicted = [Membership("detector", "2020-01", group, user)
                          for group, user in (("c0", "u02"), ("c1", "u01"))]
        self.options = dict(truth_reference="truth", detector_reference="detector",
                            active_users_by_month={"2020-01": ["u02", "isolated", "u01"]},
                            endpoint_users_by_month={"2020-01": ["u02", "u01"]})

    def test_aligns_by_user_instead_of_input_row_or_community_order(self):
        truth_before, predicted_before = self.truth.copy(), self.predicted.copy()
        frame, = align_memberships(self.truth, self.predicted, **self.options)
        self.assertEqual(frame.active_user_ids, ("isolated", "u01", "u02"))
        self.assertEqual(frame.truth_labels_all, ("K", "A", "B"))
        self.assertEqual(frame.user_ids, ("u01", "u02"))
        self.assertEqual(frame.truth_labels, ("A", "B"))
        self.assertEqual(frame.predicted_labels, ("c1", "c0"))
        self.assertEqual(self.truth, truth_before)
        self.assertEqual(self.predicted, predicted_before)

    def test_input_reordering_does_not_change_vectors_and_renaming_is_preserved(self):
        original = align_memberships(self.truth, self.predicted, **self.options)
        reordered = align_memberships(reversed(self.truth), reversed(self.predicted), **self.options)
        self.assertEqual(original, reordered)
        renamed = [Membership(row.reference_id, row.month, {"c0": "z", "c1": "a"}[row.community_id], row.user_id)
                   for row in self.predicted]
        frame, = align_memberships(self.truth, renamed, **self.options)
        self.assertEqual(frame.user_ids, original[0].user_ids)
        self.assertEqual(frame.truth_labels, original[0].truth_labels)
        self.assertEqual(frame.predicted_labels, ("a", "z"))

    def test_rejects_duplicate_missing_unknown_or_isolate_prediction_without_intersection(self):
        changes = [
            (self.truth + self.truth[:1], self.predicted),
            (self.truth[:-1], self.predicted),
            (self.truth + [Membership("truth", "2020-01", "A", "outside")], self.predicted),
            (self.truth, self.predicted + self.predicted[:1]),
            (self.truth, self.predicted[:-1]),
            (self.truth, self.predicted + [Membership("detector", "2020-01", "c1", "outside")]),
            (self.truth, self.predicted + [Membership("detector", "2020-01", "c1", "isolated")]),
        ]
        for truth, predicted in changes:
            with self.subTest(truth=truth, predicted=predicted), self.assertRaises(ValueError):
                align_memberships(truth, predicted, **self.options)

    def test_rejects_wrong_reference_or_month_and_same_truth_detector_reference(self):
        for field, value in (("reference_id", "other"), ("month", "2020-02")):
            for side in ("truth", "prediction"):
                rows = self.truth.copy() if side == "truth" else self.predicted.copy()
                row = rows[0]
                data = {"reference_id": row.reference_id, "month": row.month, "community_id": row.community_id, "user_id": row.user_id}
                data[field] = value
                rows[0] = Membership(**data)
                with self.subTest(field=field, side=side), self.assertRaises(ValueError):
                    align_memberships(rows if side == "truth" else self.truth,
                                      rows if side == "prediction" else self.predicted, **self.options)
        with self.assertRaisesRegex(ValueError, "references must differ"):
            align_memberships(self.truth, self.predicted, **{**self.options, "detector_reference": "truth"})

    def test_user_ids_are_scoped_by_month_without_inferring_group_continuity(self):
        truth = [Membership("truth", month, group, user) for month, group, user in (
            ("2020-01", "A", "u01"), ("2020-01", "B", "u02"),
            ("2020-02", "D", "u01"), ("2020-02", "C", "u02"))]
        predicted = [Membership("detector", row.month, "x" if row.user_id == "u01" else "y", row.user_id)
                     for row in reversed(truth)]
        users = {"2020-02": ["u02", "u01"], "2020-01": ["u01", "u02"]}
        frames = align_memberships(truth, predicted, truth_reference="truth", detector_reference="detector",
                                   active_users_by_month=users, endpoint_users_by_month=users)
        self.assertEqual([f.month for f in frames], ["2020-01", "2020-02"])
        self.assertEqual([f.truth_labels for f in frames], [("A", "B"), ("D", "C")])
        self.assertEqual([f.predicted_labels for f in frames], [("x", "y"), ("x", "y")])

    def test_empty_scored_and_empty_active_months_remain_explicit(self):
        frames = align_memberships([Membership("truth", "2020-01", "A", "alone")], [],
                                   truth_reference="truth", detector_reference="detector",
                                   active_users_by_month={"2020-01": ["alone"], "2020-02": []},
                                   endpoint_users_by_month={"2020-01": [], "2020-02": []})
        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0].active_user_ids, ("alone",))
        self.assertEqual(frames[0].truth_labels_all, ("A",))
        self.assertEqual(frames[1].active_user_ids, ())
        self.assertTrue(all(f.user_ids == f.truth_labels == f.predicted_labels == () for f in frames))

    def test_invalid_month_user_maps_or_nonactive_endpoint_are_rejected(self):
        invalid = [
            {"endpoint_users_by_month": {"2020-02": ["u01", "u02"]}},
            {"active_users_by_month": {}},
            {"active_users_by_month": {"2020-01": "u01"}},
            {"endpoint_users_by_month": {"2020-01": ["u01", "u01", "u02"]}},
            {"active_users_by_month": {"2020-01": ["u01", "u01", "u02", "isolated"]}},
        ]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValueError):
                align_memberships(self.truth, self.predicted, **{**self.options, **change})
        with self.assertRaisesRegex(ValueError, "endpoint is outside active"):
            align_memberships([Membership("truth", "2020-01", "A", "active")],
                              [Membership("detector", "2020-01", "x", "outside")],
                              truth_reference="truth", detector_reference="detector",
                              active_users_by_month={"2020-01": ["active"]}, endpoint_users_by_month={"2020-01": ["outside"]})

    def test_one_shot_iterables_are_materialized_once(self):
        original = align_memberships(self.truth, self.predicted, **self.options)
        actual = align_memberships(iter(self.truth), iter(self.predicted), truth_reference="truth", detector_reference="detector",
                                   active_users_by_month={"2020-01": iter(["u02", "isolated", "u01"])},
                                   endpoint_users_by_month={"2020-01": iter(["u02", "u01"])})
        self.assertEqual(actual, original)


class DetectionCountTests(unittest.TestCase):
    def setUp(self):
        DetectionAlignmentTests.setUp(self)

    def frame(self):
        frame, = align_memberships(self.truth, self.predicted, **self.options)
        return frame

    def test_isolate_stays_in_denominator_and_all_truth_group_count(self):
        counts = count_snapshot(self.frame())
        self.assertEqual((counts.active_nodes, counts.endpoint_nodes, counts.assigned_nodes, counts.isolated_nodes), (3, 2, 2, 1))
        self.assertAlmostEqual(counts.coverage, 2 / 3)
        self.assertEqual(counts.coverage_status, "defined")
        self.assertEqual((counts.true_communities_all_nodes, counts.true_communities_scored_nodes, counts.predicted_communities), (3, 2, 2))

    def test_full_coverage_and_group_counts_ignore_row_order_and_group_names(self):
        options = {**self.options, "active_users_by_month": self.options["endpoint_users_by_month"]}
        truth = [row for row in self.truth if row.user_id != "isolated"]
        original, = align_memberships(truth, self.predicted, **options)
        renamed = [Membership(row.reference_id, row.month, "renamed-" + row.community_id, row.user_id)
                   for row in reversed(self.predicted)]
        reordered, = align_memberships(reversed(truth), renamed, **options)
        self.assertEqual(count_snapshot(original), count_snapshot(reordered))
        self.assertEqual(count_snapshot(original).coverage, 1.0)
        self.assertEqual(count_snapshot(original).isolated_nodes, 0)

    def test_all_isolates_have_zero_coverage_but_empty_population_is_undefined(self):
        frames = align_memberships([Membership("truth", "2020-01", "A", "alone")], [],
                                   truth_reference="truth", detector_reference="detector",
                                   active_users_by_month={"2020-01": ["alone"], "2020-02": []},
                                   endpoint_users_by_month={"2020-01": [], "2020-02": []})
        isolated, empty = [count_snapshot(frame) for frame in frames]
        self.assertEqual((isolated.active_nodes, isolated.endpoint_nodes, isolated.assigned_nodes, isolated.isolated_nodes), (1, 0, 0, 1))
        self.assertEqual((isolated.coverage, isolated.coverage_status), (0.0, "defined"))
        self.assertEqual((isolated.true_communities_all_nodes, isolated.true_communities_scored_nodes, isolated.predicted_communities), (1, 0, 0))
        self.assertEqual((empty.active_nodes, empty.endpoint_nodes, empty.assigned_nodes, empty.isolated_nodes), (0, 0, 0, 0))
        self.assertEqual((empty.coverage, empty.coverage_status), (None, "no_active_users"))
        self.assertEqual((empty.true_communities_all_nodes, empty.true_communities_scored_nodes, empty.predicted_communities), (0, 0, 0))

    def test_singleton_and_constant_partitions_still_have_defined_counts(self):
        for users in (("u01",), ("u01", "u02")):
            with self.subTest(users=users):
                frame, = align_memberships([Membership("truth", "2020-01", "A", user) for user in users],
                                           [Membership("detector", "2020-01", "x", user) for user in users],
                                           truth_reference="truth", detector_reference="detector",
                                           active_users_by_month={"2020-01": users}, endpoint_users_by_month={"2020-01": users})
                counts = count_snapshot(frame)
                self.assertEqual(counts.coverage, 1.0)
                self.assertEqual(counts.assigned_nodes, len(users))
                self.assertEqual((counts.true_communities_all_nodes, counts.true_communities_scored_nodes, counts.predicted_communities), (1, 1, 1))

    def test_same_users_in_two_months_are_counted_per_snapshot(self):
        frames = align_memberships(
            [Membership("truth", month, group, user) for month, group, user in (
                ("2020-01", "A", "u01"), ("2020-01", "B", "u02"), ("2020-02", "C", "u01"), ("2020-02", "C", "u02"))],
            [Membership("detector", month, group, user) for month, group, user in (
                ("2020-01", "x", "u01"), ("2020-01", "y", "u02"), ("2020-02", "x", "u01"), ("2020-02", "x", "u02"))],
            truth_reference="truth", detector_reference="detector",
            active_users_by_month={month: ["u01", "u02"] for month in ("2020-01", "2020-02")},
            endpoint_users_by_month={month: ["u01", "u02"] for month in ("2020-01", "2020-02")})
        counts = [count_snapshot(frame) for frame in frames]
        self.assertEqual([row.month for row in counts], ["2020-01", "2020-02"])
        self.assertEqual([row.active_nodes for row in counts], [2, 2])
        self.assertEqual([row.true_communities_all_nodes for row in counts], [2, 1])
        self.assertEqual([row.predicted_communities for row in counts], [2, 1])

    def test_manually_malformed_aligned_snapshots_are_rejected_before_counting(self):
        frame = self.frame()
        invalid = [None, replace(frame, month="2020-13"), replace(frame, user_ids=("u01", "u01")),
                   replace(frame, user_ids=("u02", "u01")), replace(frame, predicted_labels=("x",)),
                   replace(frame, truth_labels_all=("K", "A")), replace(frame, user_ids=("u01", "outside")),
                   replace(frame, truth_labels=("B", "A")), replace(frame, predicted_labels=("", "x")),
                   replace(frame, user_ids=("", "u02")), replace(frame, predicted_labels=(True, "x")),
                   replace(frame, active_user_ids=list(frame.active_user_ids))]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                count_snapshot(value)
