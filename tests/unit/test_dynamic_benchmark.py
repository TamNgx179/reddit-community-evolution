"""Checks for the stable sampler's edge model, node coverage and seed protocol."""

from itertools import combinations
import json
import os
import random
import subprocess
import sys
import unittest

from reddit_sna.benchmarks.dynamic import sample_snapshots
from reddit_sna.benchmarks.scenarios import build_memberships
from reddit_sna.contracts import Membership


class StableGraphSamplerTests(unittest.TestCase):
    def setUp(self):
        self.reference = "truth-dev-stable-easy-g11"
        self.rows = build_memberships("stable", self.reference)
        self.main = {f"u{i:03d}" for i in range(1, 13)}
        self.background = {f"u{i:03d}" for i in range(101, 113)}
        self.users = {month: self.main | self.background for month in ("2020-01", "2020-02")}

    def sample(self, rows=None, **overrides):
        args = dict(expected_reference=self.reference, expected_users_by_month=self.users)
        args.update(overrides)
        return sample_snapshots(self.rows if rows is None else rows, **args)

    def test_default_stable_seed_11_keeps_every_node_and_valid_canonical_edges(self):
        snapshots = self.sample()
        self.assertEqual([snapshot.month for snapshot in snapshots], ["2020-01", "2020-02"])
        for snapshot in snapshots:
            self.assertEqual(snapshot.nodes, tuple(sorted(self.main | self.background)))
            pairs = [(edge.source_user_id, edge.target_user_id) for edge in snapshot.edges]
            self.assertTrue(pairs)
            self.assertEqual(pairs, sorted(set(pairs)))
            for edge in snapshot.edges:
                self.assertEqual(edge.month, snapshot.month)
                self.assertLess(edge.source_user_id, edge.target_user_id)
                self.assertIn(edge.source_user_id, snapshot.nodes)
                self.assertIn(edge.target_user_id, snapshot.nodes)
                self.assertEqual(edge.weight, 1.0)
        # Seed 11 samples a fresh edge set in the second stable-membership month.
        self.assertNotEqual([(e.source_user_id, e.target_user_id) for e in snapshots[0].edges],
                            [(e.source_user_id, e.target_user_id) for e in snapshots[1].edges])

    def test_probability_extremes_distinguish_within_and_between_groups(self):
        within = set(combinations(sorted(self.main), 2)) | set(combinations(sorted(self.background), 2))
        between = {(source, target) for source in self.main for target in self.background}
        for p_in, p_out, expected in ((1, 0, within), (0, 1, between)):
            with self.subTest(p_in=p_in, p_out=p_out):
                for snapshot in self.sample(p_in=p_in, p_out=p_out):
                    self.assertEqual({(edge.source_user_id, edge.target_user_id) for edge in snapshot.edges}, expected)
                    self.assertEqual(len(snapshot.edges), 132 if p_in else 144)

    def test_zero_probability_preserves_all_isolates_without_adding_edges(self):
        for snapshot in self.sample(p_in=0, p_out=0):
            self.assertEqual(len(snapshot.nodes), 24)
            self.assertEqual(snapshot.edges, ())

    def test_unit_probability_creates_each_undirected_pair_once(self):
        for snapshot in self.sample(p_in=1, p_out=1):
            self.assertEqual(len(snapshot.edges), 276)
            self.assertEqual([(edge.source_user_id, edge.target_user_id) for edge in snapshot.edges],
                             list(combinations(snapshot.nodes, 2)))

    def test_results_ignore_membership_user_month_and_community_iteration_order(self):
        # Renaming local groups preserves the planted same/different relation.
        renamed = [Membership(row.reference_id, row.month, "renamed-" + row.community_id, row.user_id)
                   for row in reversed(self.rows)]
        users = {month: reversed(sorted(self.users[month])) for month in reversed(tuple(self.users))}
        expected = self.sample()
        self.assertEqual(self.sample(renamed, expected_users_by_month=users), expected)
        self.assertEqual(self.sample(), expected)
        self.assertNotEqual(self.sample(generator_seed=12), expected)

    def test_observed_empty_month_and_year_boundary_are_preserved(self):
        rows = build_memberships("stable", self.reference, start_month="2020-12")
        users = {"2020-12": self.main | self.background, "2021-01": self.main | self.background}
        snapshots = self.sample(rows, expected_users_by_month=users)
        self.assertEqual([snapshot.month for snapshot in snapshots], ["2020-12", "2021-01"])
        partial_rows = [row for row in rows if row.month == "2020-12"]
        users["2021-01"] = []
        empty = self.sample(partial_rows, expected_users_by_month=users)
        self.assertEqual(empty[1].nodes, ())
        self.assertEqual(empty[1].edges, ())

    def test_sampling_does_not_change_global_random_state(self):
        before = random.getstate()
        self.sample()
        self.assertEqual(random.getstate(), before)

    def test_invalid_seed_or_probabilities_are_rejected(self):
        for seed in (True, -1, 2**32, 11.0, "11", None):
            with self.subTest(seed=seed), self.assertRaisesRegex(ValueError, "generator_seed"):
                self.sample(generator_seed=seed)
        for field in ("p_in", "p_out"):
            for probability in (-0.1, 1.1, float("nan"), float("inf"), True, "0.5", None):
                with self.subTest(field=field, probability=probability), self.assertRaisesRegex(ValueError, field):
                    self.sample(**{field: probability})

    def test_bad_membership_scope_duplicates_or_coverage_are_rejected(self):
        variants = (
            (self.rows[1:], "missing expected users"),
            ((*self.rows, self.rows[0]), "duplicate membership"),
            ((*self.rows, Membership(self.reference, "2020-01", "A", "outside")), "unexpected user"),
            ((Membership("other", "2020-01", "A", "u001"), *self.rows[1:]), "reference"),
            ((*self.rows, Membership(self.reference, "2020-03", "A", "u001")), "declared months"),
        )
        for rows, message in variants:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.sample(rows)

    def test_graph_records_repeat_in_fresh_processes_with_different_hash_seeds(self):
        script = """
import json
from reddit_sna.benchmarks.dynamic import sample_snapshots
from reddit_sna.benchmarks.scenarios import build_memberships
rows = set(build_memberships("stable", "truth-process"))
users = {month: {row.user_id for row in rows if row.month == month}
         for month in {"2020-01", "2020-02"}}
snapshots = sample_snapshots(rows, expected_reference="truth-process", expected_users_by_month=users)
print(json.dumps([[s.month, s.nodes, [[e.source_user_id, e.target_user_id, e.weight] for e in s.edges]]
                  for s in snapshots]))
"""
        outputs = []
        for seed in ("0", "137"):
            completed = subprocess.run(
                [sys.executable, "-c", script], env=dict(os.environ, PYTHONHASHSEED=seed),
                capture_output=True, text=True, encoding="utf-8", timeout=20,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            outputs.append(json.loads(completed.stdout))
        self.assertEqual(outputs[0], outputs[1])
        actual = self.sample()
        self.assertEqual(outputs[0], [[snapshot.month, list(snapshot.nodes),
                                      [[edge.source_user_id, edge.target_user_id, edge.weight]
                                       for edge in snapshot.edges]] for snapshot in actual])
