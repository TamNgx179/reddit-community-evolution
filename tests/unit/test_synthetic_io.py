"""CSV contract checks with temporary synthetic files only."""

import csv
from pathlib import Path
import tempfile
import unittest

from reddit_sna.benchmarks.io import (
    read_memberships, read_nodes, validate_memberships, write_memberships, write_nodes,
)
from reddit_sna.benchmarks.scenarios import build_memberships
from reddit_sna.contracts import Membership


class SyntheticCsvTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="reddit-synthetic-io-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.reference = "truth-example"
        self.rows = build_memberships("grow", self.reference)
        self.nodes = {
            month: tuple(row.user_id for row in self.rows if row.month == month)
            for month in ("2020-01", "2020-02")
        }
        self.expected = {
            "expected_reference": self.reference,
            "expected_users_by_month": self.nodes,
        }

    def test_scenarios_round_trip_against_their_monthly_node_files(self):
        for scenario in ("stable", "grow"):
            with self.subTest(scenario=scenario):
                rows = build_memberships(scenario, self.reference)
                nodes = {}
                for month in ("2020-01", "2020-02"):
                    path = self.root / f"{scenario}-{month}-nodes.csv"
                    users = [row.user_id for row in rows if row.month == month]
                    write_nodes(path, month, reversed(users))
                    nodes[month] = read_nodes(path, expected_month=month)
                expected = dict(self.expected, expected_users_by_month=nodes)
                path = self.root / f"{scenario}-membership.csv"
                write_memberships(path, reversed(rows), **expected)
                self.assertEqual(read_memberships(path, **expected), rows)
                with path.open(encoding="utf-8", newline="") as handle:
                    table = list(csv.reader(handle))
                self.assertEqual(table[0], ["reference_id", "month", "community_id", "user_id"])
                self.assertEqual(len(table) - 1, 48 if scenario == "stable" else 54)

    def test_utf8_and_csv_quoting_preserve_identifiers(self):
        uid = 'người,dùng "mẫu"'
        rows = (Membership("tham chiếu", "2020-01", "nhóm, A", uid),)
        expected = {"expected_reference": "tham chiếu", "expected_users_by_month": {"2020-01": [uid]}}
        nodes_path, membership_path = self.root / "nodes.csv", self.root / "membership.csv"
        write_nodes(nodes_path, "2020-01", [uid])
        write_memberships(membership_path, rows, **expected)
        self.assertEqual(read_nodes(nodes_path, expected_month="2020-01"), (uid,))
        self.assertEqual(read_memberships(membership_path, **expected), rows)

    def test_empty_observed_month_is_explicit_and_round_trips(self):
        nodes_path, membership_path = self.root / "nodes.csv", self.root / "membership.csv"
        expected = dict(self.expected, expected_users_by_month={"2020-01": []})
        write_nodes(nodes_path, "2020-01", [])
        write_memberships(membership_path, [], **expected)
        self.assertEqual(read_nodes(nodes_path, expected_month="2020-01"), ())
        self.assertEqual(read_memberships(membership_path, **expected), ())
        self.assertEqual(nodes_path.read_text(encoding="utf-8"), "month,user_id\n")
        self.assertEqual(membership_path.read_text(encoding="utf-8"), "reference_id,month,community_id,user_id\n")

    def test_duplicate_nodes_are_rejected_on_read_and_before_write(self):
        path = self.root / "duplicate.csv"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            write_nodes(path, "2020-01", ["u1", "u1"])
        self.assertFalse(path.exists())
        path.write_text("month,user_id\n2020-01,u1\n2020-01,u1\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            read_nodes(path, expected_month="2020-01")

    def test_duplicate_membership_is_rejected_even_for_different_communities(self):
        for duplicate in (self.rows[0], Membership(self.reference, "2020-01", "another-group", self.rows[0].user_id)):
            with self.subTest(duplicate=duplicate), self.assertRaisesRegex(ValueError, "duplicate membership"):
                validate_memberships((*self.rows, duplicate), **self.expected)

    def test_missing_users_and_missing_month_population_are_rejected(self):
        for incomplete in (self.rows[1:], tuple(row for row in self.rows if row.month == "2020-01"), ()):
            with self.subTest(count=len(incomplete)), self.assertRaisesRegex(ValueError, "missing expected users"):
                validate_memberships(incomplete, **self.expected)

    def test_unexpected_user_is_rejected_instead_of_taking_an_intersection(self):
        extra = Membership(self.reference, "2020-01", "A", "outside-dataset")
        with self.assertRaisesRegex(ValueError, "unexpected user"):
            validate_memberships((*self.rows, extra), **self.expected)

    def test_mixed_or_wrong_references_are_rejected_on_read_and_write(self):
        altered = Membership("another-reference", "2020-01", "A", self.rows[0].user_id)
        with self.assertRaisesRegex(ValueError, "reference"):
            validate_memberships((altered, *self.rows[1:]), **self.expected)
        path = self.root / "wrong-reference.csv"
        path.write_text("reference_id,month,community_id,user_id\nother,2020-01,A,u1\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "reference"):
            read_memberships(path, **self.expected)
        with self.assertRaisesRegex(ValueError, "reference"):
            write_memberships(self.root / "not-created.csv", self.rows, **dict(self.expected, expected_reference="wrong"))
        self.assertFalse((self.root / "not-created.csv").exists())

    def test_unexpected_or_nonconsecutive_membership_months_are_rejected(self):
        extra = Membership(self.reference, "2020-03", "A", "u1")
        with self.assertRaisesRegex(ValueError, "declared months"):
            validate_memberships((*self.rows, extra), **self.expected)
        expected = dict(self.expected, expected_users_by_month={"2020-01": [], "2020-03": []})
        with self.assertRaisesRegex(ValueError, "consecutive"):
            validate_memberships([], **expected)

    def test_readers_require_exact_headers(self):
        cases = (
            (read_nodes, {"expected_month": "2020-01"}, ("", "user_id,month\n", "month,user_id,extra\n", "month,month\n", "\ufeffmonth,user_id\n")),
            (read_memberships, self.expected, ("", "month,reference_id,community_id,user_id\n", "reference_id,month,community_id\n", "reference_id,month,community_id,user_id,extra\n")),
        )
        path = self.root / "bad-header.csv"
        for reader, kwargs, texts in cases:
            for text in texts:
                with self.subTest(reader=reader.__name__, text=text):
                    path.write_text(text, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "header"):
                        reader(path, **kwargs)

    def test_readers_reject_row_width_errors_and_malformed_csv(self):
        cases = (
            (read_nodes, {"expected_month": "2020-01"}, "month,user_id\n", ("2020-01\n", "2020-01,u1,extra\n", "\n", '2020-01,"unterminated\n')),
            (read_memberships, self.expected, "reference_id,month,community_id,user_id\n", ("truth-example,2020-01,A\n", "truth-example,2020-01,A,u1,extra\n", "\n", 'truth-example,2020-01,A,"unterminated\n')),
        )
        path = self.root / "bad-row.csv"
        for reader, kwargs, header, rows in cases:
            for row in rows:
                with self.subTest(reader=reader.__name__, row=row):
                    path.write_text(header + row, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        reader(path, **kwargs)

    def test_empty_identifiers_in_csv_are_rejected(self):
        path = self.root / "empty-id.csv"
        for row in (",2020-01,A,u1", "truth-example,,A,u1", "truth-example,2020-01, ,u1", "truth-example,2020-01,A,"):
            with self.subTest(row=row):
                path.write_text("reference_id,month,community_id,user_id\n" + row + "\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_memberships(path, **self.expected)
        path.write_text("month,user_id\n2020-01, \n", encoding="utf-8")
        with self.assertRaises(ValueError):
            read_nodes(path, expected_month="2020-01")

    def test_node_month_must_match_explicit_expectation(self):
        path = self.root / "wrong-month.csv"
        path.write_text("month,user_id\n2020-02,u1\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "month"):
            read_nodes(path, expected_month="2020-01")
        for month in ("2020-00", "2020-1", None):
            with self.subTest(month=month), self.assertRaises(ValueError):
                write_nodes(self.root / "not-created.csv", month, ["u1"])
        self.assertFalse((self.root / "not-created.csv").exists())

    def test_invalid_expectations_and_non_membership_records_are_rejected(self):
        for users in ({}, {"2020-00": []}, {"2020-01": ["u1", "u1"]}, {"2020-01": [None]}, {"2020-01": "u1"}):
            with self.subTest(users=users), self.assertRaises(ValueError):
                validate_memberships([], **dict(self.expected, expected_users_by_month=users))
        for reference in ("", " ", None):
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                validate_memberships(self.rows, **dict(self.expected, expected_reference=reference))
        with self.assertRaisesRegex(ValueError, "Membership records"):
            validate_memberships([{"month": "2020-01"}], **self.expected)

    def test_writers_preserve_existing_files(self):
        path = self.root / "existing.csv"
        original = b"existing output must survive\n"
        path.write_bytes(original)
        for action in (
            lambda: write_nodes(path, "2020-01", ["u1"]),
            lambda: write_memberships(path, self.rows, **self.expected),
        ):
            with self.assertRaises(FileExistsError):
                action()
            self.assertEqual(path.read_bytes(), original)

    def test_invalid_writes_do_not_create_files_or_parent_directories(self):
        path = self.root / "not-created.csv"
        with self.assertRaises(ValueError):
            write_memberships(path, self.rows[1:], **self.expected)
        self.assertFalse(path.exists())
        for users in ([" "], [None], "u1", None):
            with self.subTest(users=users), self.assertRaises(ValueError):
                write_nodes(path, "2020-01", users)
            self.assertFalse(path.exists())
        absent_parent = self.root / "absent" / "nodes.csv"
        with self.assertRaises(FileNotFoundError):
            write_nodes(absent_parent, "2020-01", ["u1"])
        self.assertFalse(absent_parent.parent.exists())

    def test_read_errors_do_not_modify_the_input_file(self):
        path = self.root / "bad-input.csv"
        original = b"reference_id,month,community_id,user_id\ntruth-example,2020-01,A,outside\n"
        path.write_bytes(original)
        with self.assertRaises(ValueError):
            read_memberships(path, **self.expected)
        self.assertEqual(path.read_bytes(), original)

    def test_canonical_output_bytes_do_not_depend_on_input_record_order(self):
        first, second = self.root / "first.csv", self.root / "second.csv"
        write_memberships(first, self.rows, **self.expected)
        write_memberships(second, reversed(self.rows), **self.expected)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertNotIn(b"\r\n", first.read_bytes())
        nodes_first, nodes_second = self.root / "nodes-first.csv", self.root / "nodes-second.csv"
        write_nodes(nodes_first, "2020-01", self.nodes["2020-01"])
        write_nodes(nodes_second, "2020-01", reversed(self.nodes["2020-01"]))
        self.assertEqual(nodes_first.read_bytes(), nodes_second.read_bytes())
