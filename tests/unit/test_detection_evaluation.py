"""Detection input alignment, before any AMI or coverage calculation."""

from dataclasses import replace
import importlib.util
import unittest
from unittest.mock import patch

from reddit_sna.contracts import Membership
from reddit_sna.evaluation.detection import AMI_POLICY, align_memberships, count_snapshot, score_snapshot


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


def ami_frame(truth, predicted):
    users = tuple(f"u{index:03}" for index in range(len(truth)))
    frame, = align_memberships(
        [Membership("truth", "2020-01", label, user) for user, label in zip(users, truth, strict=True)],
        [Membership("detector", "2020-01", label, user) for user, label in zip(users, predicted, strict=True)],
        truth_reference="truth", detector_reference="detector",
        active_users_by_month={"2020-01": users}, endpoint_users_by_month={"2020-01": users})
    return frame


class AMIPolicyTests(unittest.TestCase):
    def test_null_cases_have_explicit_status_reason_and_never_import_sklearn(self):
        cases = [
            ((), (), "empty_scored", "no_scored_users"),
            (("A",), ("x",), "insufficient_users", "fewer_than_2_scored_users"),
            (tuple("AAAA"), tuple("xxyy"), "degenerate_partition", "truth_constant"),
            (tuple("AABB"), tuple("xxxx"), "degenerate_partition", "prediction_constant"),
            (tuple("AAAA"), tuple("xxxx"), "degenerate_partition", "truth_constant,prediction_constant"),
            (tuple("ABCD"), tuple("xxyy"), "degenerate_partition", "truth_all_singletons"),
            (tuple("AABB"), tuple("wxyz"), "degenerate_partition", "prediction_all_singletons"),
            (tuple("ABCD"), tuple("wxyz"), "degenerate_partition", "truth_all_singletons,prediction_all_singletons"),
            (tuple("AAAA"), tuple("wxyz"), "degenerate_partition", "truth_constant,prediction_all_singletons"),
            (tuple("AB"), tuple("xy"), "degenerate_partition", "truth_all_singletons,prediction_all_singletons"),
        ]
        original_import = __import__
        def no_sklearn(name, *args, **kwargs):
            if name.startswith("sklearn"):
                raise AssertionError("null cases must not invoke the metric backend")
            return original_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=no_sklearn):
            for truth, predicted, status, reason in cases:
                with self.subTest(truth=truth, predicted=predicted):
                    result = score_snapshot(ami_frame(truth, predicted))
                    self.assertIsNone(result.ami)
                    self.assertEqual((result.ami_status, result.ami_reason), (status, reason))
                    self.assertEqual(result.n_scored_users, len(truth))
                    self.assertEqual((result.ami_policy_id, result.ami_average_method), ("synthetic-ami-v1", "arithmetic"))

    def test_invalid_memberships_are_errors_before_missing_or_degenerate_policy(self):
        frame = ami_frame(tuple("AABB"), tuple("xxyy"))
        for invalid in (replace(frame, predicted_labels=()), replace(frame, user_ids=("u000",) * 4),
                        replace(frame, truth_labels=tuple("BBAA")), replace(frame, month="2020-13")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                score_snapshot(invalid)

    def test_policy_is_immutable_and_json_copy_cannot_change_scoring_policy(self):
        with self.assertRaises(TypeError):
            AMI_POLICY["average_method"] = "max"
        copied = dict(AMI_POLICY)
        copied["average_method"] = "max"
        self.assertEqual(AMI_POLICY["average_method"], "arithmetic")

    def test_missing_sklearn_reports_installable_evaluation_extra(self):
        original_import = __import__
        def missing(name, *args, **kwargs):
            if name == "sklearn.metrics":
                raise ModuleNotFoundError("No module named sklearn", name="sklearn")
            return original_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=missing), self.assertRaisesRegex(ImportError, r"\.\[evaluation\]"):
            score_snapshot(ami_frame(tuple("AABB"), tuple("xxyy")))

    def test_missing_backend_transitive_dependency_is_not_misreported_as_null_ami(self):
        original_import = __import__
        def missing(name, *args, **kwargs):
            if name == "sklearn.metrics":
                raise ModuleNotFoundError("No module named scipy", name="scipy")
            return original_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=missing), self.assertRaises(ModuleNotFoundError) as error:
            score_snapshot(ami_frame(tuple("AABB"), tuple("xxyy")))
        self.assertEqual(error.exception.name, "scipy")


@unittest.skipUnless(importlib.util.find_spec("sklearn"), "install [evaluation] for AMI scoring tests")
class AMIScoringTests(unittest.TestCase):
    def test_identical_detector_runs_can_agree_while_both_disagree_with_truth(self):
        from sklearn.metrics import adjusted_rand_score
        truth, first, second = tuple("AABB"), tuple("xyxy"), tuple("pqpq")
        self.assertAlmostEqual(float(adjusted_rand_score(first, second)), 1.0)
        for predicted in (first, second):
            with self.subTest(predicted=predicted):
                result = score_snapshot(ami_frame(truth, predicted))
                self.assertEqual(result.ami_status, "ok")
                self.assertAlmostEqual(result.ami, -0.5, places=12)
        self.assertAlmostEqual(score_snapshot(ami_frame(truth, tuple("xxyy"))).ami, 1.0)

    def test_nontrivial_perfect_partition_returns_one(self):
        result = score_snapshot(ami_frame(tuple("AABB"), tuple("yyxx")))
        self.assertAlmostEqual(result.ami, 1.0, places=12)
        self.assertEqual(result.ami_status, "ok")
        self.assertIsNone(result.ami_reason)
        self.assertEqual(result.n_scored_users, 4)

    def test_reordering_csv_rows_and_renaming_groups_preserves_ami(self):
        truth = [Membership("truth", "2020-01", group, f"u{i}") for i, group in enumerate("AAABBB")]
        predicted = [Membership("detector", "2020-01", group, f"u{i}") for i, group in enumerate("xxxxyy")]
        users = {"2020-01": [f"u{i}" for i in range(6)]}
        options = dict(truth_reference="truth", detector_reference="detector", active_users_by_month=users, endpoint_users_by_month=users)
        frame, = align_memberships(truth, predicted, **options)
        changed, = align_memberships(reversed(truth), [Membership(row.reference_id, row.month, "name-" + row.community_id, row.user_id)
                                                     for row in reversed(predicted)], **options)
        self.assertAlmostEqual(score_snapshot(frame).ami, score_snapshot(changed).ami, places=12)

    def test_negative_score_is_preserved_instead_of_clamped_to_zero(self):
        result = score_snapshot(ami_frame(tuple("AABB"), tuple("xyxy")))
        self.assertEqual(result.ami_status, "ok")
        self.assertLess(result.ami, 0)
        self.assertAlmostEqual(result.ami, -0.5, places=12)

    def test_score_matches_library_arithmetic_method_and_is_symmetric(self):
        from sklearn.metrics import adjusted_mutual_info_score
        truth, predicted = tuple("AAABBB"), tuple("xxxxyy")
        result = score_snapshot(ami_frame(truth, predicted))
        expected = adjusted_mutual_info_score(truth, predicted, average_method="arithmetic")
        self.assertAlmostEqual(result.ami, float(expected), places=12)
        self.assertAlmostEqual(result.ami, score_snapshot(ami_frame(predicted, truth)).ami, places=12)

    def test_isolate_truth_is_excluded_from_ami_but_retained_in_coverage(self):
        frame = ami_frame(tuple("AABB"), tuple("xxyy"))
        frame = replace(frame, active_user_ids=frame.active_user_ids + ("zzz-isolated",), truth_labels_all=frame.truth_labels_all + ("K",))
        result = score_snapshot(frame)
        self.assertAlmostEqual(result.ami, 1.0, places=12)
        self.assertEqual(result.n_scored_users, 4)
        self.assertEqual(count_snapshot(frame).coverage, 4 / 5)

    def test_nonfinite_scores_and_backend_failures_raise_instead_of_filling_defaults(self):
        frame = ami_frame(tuple("AABB"), tuple("xxyy"))
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), patch("sklearn.metrics.adjusted_mutual_info_score", return_value=value), self.assertRaisesRegex(ValueError, "nonfinite"):
                score_snapshot(frame)
        with patch("sklearn.metrics.adjusted_mutual_info_score", side_effect=RuntimeError("backend failure")), self.assertRaisesRegex(RuntimeError, "backend failure"):
            score_snapshot(frame)
