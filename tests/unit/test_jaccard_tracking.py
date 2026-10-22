import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from reddit_sna.evaluation.tracking import (
    evaluate_events,
    map_source_communities,
    project_detector_events,
)
from reddit_sna.contracts import Membership
from reddit_sna.tracking.jaccard import track
from reddit_sna.tracking.membership import (
    groups_by_month,
    groups_from_rows,
    read_memberships,
)


class JaccardTrackingTests(unittest.TestCase):
    def test_membership_csv_reads_multiple_months_and_groups_them(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "membership.csv"
            path.write_text(
                "reference_id,month,community_id,user_id\n"
                "truth-001,2020-01,A,u1\n"
                "truth-001,2020-01,K,k1\n"
                "truth-001,2020-02,C,u1\n"
                "truth-001,2020-02,K,k1\n",
                encoding="utf-8",
            )
            rows = read_memberships(
                path,
                expected_reference="truth-001",
                expected_users_by_month={
                    "2020-01": ("u1", "k1"),
                    "2020-02": ("u1", "k1"),
                },
            )
        grouped = groups_by_month(rows, expected_reference="truth-001")
        self.assertEqual(grouped["2020-01"]["A"], frozenset({"u1"}))
        self.assertEqual(grouped["2020-02"]["C"], frozenset({"u1"}))
        self.assertEqual(
            groups_from_rows(rows, month="2020-01")["K"],
            frozenset({"k1"}),
        )

    def test_groups_from_rows_requires_month_for_multiple_months(self):
        rows = (
            Membership("truth-001", "2020-01", "A", "u1"),
            Membership("truth-001", "2020-02", "C", "u1"),
        )
        with self.assertRaisesRegex(ValueError, "specify month"):
            groups_from_rows(rows)

    def test_membership_csv_rejects_wrong_header_order(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "membership.csv"
            path.write_text(
                "month,reference_id,community_id,user_id\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "header"):
                read_memberships(path)

    def test_six_truth_events(self):
        cases = (
            ({"A": {"1", "2", "3"}}, {"C": {"1", "2", "3"}}, "stable"),
            ({"A": {"1", "2", "3"}}, {"C": {"1", "2", "3", "4"}}, "grow"),
            ({"A": {"1", "2", "3", "4"}}, {"C": {"1", "2", "3"}}, "shrink"),
            (
                {"A": {"1", "2"}, "B": {"3", "4"}},
                {"C": {"1", "2", "3", "4"}},
                "merge",
            ),
            (
                {"A": {"1", "2", "3", "4"}},
                {"B": {"1", "2"}, "C": {"3", "4"}},
                "split",
            ),
            ({"A": {"1", "2"}}, {}, "dissolve"),
        )
        for source, target, expected in cases:
            with self.subTest(expected=expected):
                result = track(source, target)
                self.assertEqual(result["events"][0]["event"], expected)

    def test_threshold_and_unobserved_successor(self):
        self.assertEqual(
            track({"A": {"1", "2", "3"}}, {"C": {"4"}})["events"][0]["event"],
            "dissolve",
        )
        result = track({"A": {"1"}}, {}, target_observed=False)
        self.assertEqual(result["events"], [])
        self.assertFalse(result["diagnostics"]["target_observed"])

    def test_ambiguous_split_is_reported(self):
        result = track(
            {"A": {"1", "2"}, "B": {"3", "4"}},
            {"C": {"1", "3"}, "D": {"2", "4"}},
        )
        self.assertEqual(result["events"][0]["event"], "split")
        self.assertEqual(result["diagnostics"]["ambiguous_source_count"], 2)

    def test_evaluation_retains_unmatched_sources(self):
        result = evaluate_events(
            [
                {"source_community_id": "A", "event": "stable"},
                {"source_community_id": "B", "event": "grow"},
            ],
            [{"source_community_id": "A", "event": "stable"}],
        )
        self.assertEqual(result["matched_support"], 1)
        self.assertEqual(result["support"], 2)
        self.assertEqual(result["confusion_matrix"]["grow"]["__unmatched__"], 1)
        self.assertEqual(result["unmatched_truth_sources"], ["B"])
        self.assertEqual(result["extra_prediction_sources"], [])

    def test_evaluation_reports_extra_prediction_sources(self):
        result = evaluate_events(
            [{"source_community_id": "A", "event": "stable"}],
            [
                {"source_community_id": "A", "event": "stable"},
                {"source_community_id": "EXTRA", "event": "grow"},
            ],
        )
        self.assertEqual(result["extra_prediction_sources"], ["EXTRA"])

    def test_mapping_is_greedy_and_deterministic(self):
        result = map_source_communities(
            {"A": {"1", "2"}, "B": {"3", "4"}},
            {"c0": {"1", "2"}, "c1": {"3"}},
        )
        self.assertEqual(len(result["mapping"]), 2)
        self.assertEqual(result["unmatched_truth"], [])
        self.assertEqual(result["extra_detector"], [])

    def test_detector_events_are_projected_after_mapping(self):
        result = project_detector_events(
            {"A": {"1", "2"}, "B": {"3", "4"}},
            {"c0": {"1", "2"}, "c1": {"3", "4"}},
            [
                {"source_community_id": "c0", "event": "stable"},
                {"source_community_id": "c1", "event": "merge"},
            ],
        )
        self.assertEqual(
            [row["event"] for row in result["event_predictions"]],
            ["stable", "merge"],
        )
        self.assertEqual(result["missing_detector_events"], [])

    def test_duplicate_truth_sources_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            evaluate_events(
                [
                    {"source_community_id": "A", "event": "stable"},
                    {"source_community_id": "A", "event": "grow"},
                ],
                [],
            )
