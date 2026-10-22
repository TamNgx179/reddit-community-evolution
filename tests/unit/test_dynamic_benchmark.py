"""Six-case sampler, seed/order protocol and explicit tiny/isolate diagnostics."""

from copy import deepcopy
from itertools import combinations
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from reddit_sna.benchmarks.dynamic import sample_snapshots
from reddit_sna.benchmarks.io import (
    EDGE_COLUMNS, read_edges, read_memberships, read_nodes,
    write_edges, write_memberships, write_nodes,
)
from reddit_sna.benchmarks.scenarios import SCENARIOS, build_memberships, build_transitions
from reddit_sna.contracts import Membership

DIAGNOSTICS = Path(__file__).resolve().parents[1] / "fixtures/dynamic_diagnostics.json"


def diagnostic_inputs(case, reference):
    """Inputs are explicit fixture populations, independent of generated edges."""
    users = {month: [uid for ids in groups.values() for uid in ids]
             for month, groups in case["groups_by_month"].items()}
    rows = [Membership(reference, month, community, uid)
            for month, groups in case["groups_by_month"].items()
            for community, ids in groups.items() for uid in ids]
    return rows, users


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

    def test_seed_range_endpoints_replay_without_mutating_inputs(self):
        rows, users = self.rows, deepcopy(self.users)
        results = []
        for seed in (0, 2**32 - 1):
            with self.subTest(seed=seed):
                first = self.sample(generator_seed=seed)
                self.assertEqual(self.sample(generator_seed=seed), first)
                self.assertTrue(all(s.edges for s in first))
                results.append(first)
        self.assertNotEqual(results[0], results[1])
        self.assertEqual(self.rows, rows)
        self.assertEqual(self.users, users)

    def test_changing_one_probability_keeps_other_pairs_random_draws(self):
        # Changing p_in must not move cross-group draws along the RNG stream;
        # changing p_out must not move within-group draws. Includes p=0 and 1.
        def relation_edges(snapshots, within):
            return [tuple((e.source_user_id, e.target_user_id) for e in s.edges
                          if ((e.source_user_id in self.main) == (e.target_user_id in self.main)) == within)
                    for s in snapshots]

        cross_zero = relation_edges(self.sample(p_in=0, p_out=0.5), False)
        cross_one = relation_edges(self.sample(p_in=1, p_out=0.5), False)
        self.assertEqual(cross_zero, cross_one)
        self.assertTrue(all(cross_zero))
        within_zero = relation_edges(self.sample(p_in=0.5, p_out=0), True)
        within_one = relation_edges(self.sample(p_in=0.5, p_out=1), True)
        self.assertEqual(within_zero, within_one)
        self.assertTrue(all(within_zero))

    def test_invalid_registry_or_reference_is_rejected_before_sampling(self):
        cases = [dict(expected_users_by_month=value) for value in (
            {}, None, {"2020-01": "a"}, {"2020-01": [None]},
            {"2020-01": ["a", "a"]}, {"2020-13": []},
            {"2020-01": self.main, "2020-03": self.main},
        )]
        cases += [dict(expected_reference=value) for value in ("", " ", None)]
        with patch("reddit_sna.benchmarks.dynamic.random.Random", side_effect=AssertionError("must validate first")):
            for overrides in cases:
                with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                    self.sample(**overrides)

    def test_all_six_graphs_repeat_in_fresh_processes_with_different_hash_seeds(self):
        script = """
import json
from reddit_sna.benchmarks.dynamic import sample_snapshots
from reddit_sna.benchmarks.scenarios import SCENARIOS, build_memberships
result = {}
for case in SCENARIOS:
    rows = set(build_memberships(case, "truth-process"))
    users = {month: {row.user_id for row in rows if row.month == month}
             for month in {"2020-01", "2020-02"}}
    snapshots = sample_snapshots(rows, expected_reference="truth-process", expected_users_by_month=users)
    result[case] = [[s.month, s.nodes, [[e.source_user_id, e.target_user_id, e.weight] for e in s.edges]]
                    for s in snapshots]
print(json.dumps(result, sort_keys=True))
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
        for case in SCENARIOS:
            rows = build_memberships(case, "truth-process")
            users = {m: [r.user_id for r in rows if r.month == m] for m in ("2020-01", "2020-02")}
            actual = sample_snapshots(rows, expected_reference="truth-process", expected_users_by_month=users)
            self.assertEqual(outputs[0][case], [[s.month, list(s.nodes),
                                               [[e.source_user_id, e.target_user_id, e.weight] for e in s.edges]]
                                              for s in actual])


class SixCaseSamplerTests(unittest.TestCase):
    def setUp(self):
        self.reference = "truth-six-case-sampler"
        main12 = {f"u{i:03d}" for i in range(1, 13)}
        other12 = {f"u{i:03d}" for i in range(13, 25)}
        main18 = {f"u{i:03d}" for i in range(1, 19)}
        self.background = {f"u{i:03d}" for i in range(101, 113)}
        self.populations = {
            "stable": ({"A": main12}, {"C": main12}),
            "grow": ({"A": main12}, {"C": main18}),
            "shrink": ({"A": main18}, {"C": main12}),
            "merge": ({"A": main12, "B": other12}, {"C": main12 | other12}),
            "split": ({"A": main12 | other12}, {"B": main12, "C": other12}),
            "dissolve": ({"A": main12}, {}),
        }
        self.expected_links = {
            "stable": [("A", "C"), ("K", "K")], "grow": [("A", "C"), ("K", "K")],
            "shrink": [("A", "C"), ("K", "K")], "merge": [("A", "C"), ("B", "C"), ("K", "K")],
            "split": [("A", "B"), ("A", "C"), ("K", "K")], "dissolve": [("K", "K")],
        }

    def inputs(self, case):
        groups = {m: dict(self.populations[case][i], K=self.background)
                  for i, m in enumerate(("2020-01", "2020-02"))}
        users = {m: set().union(*partition.values()) for m, partition in groups.items()}
        return build_memberships(case, self.reference), groups, users

    def test_six_cases_across_development_seeds_preserve_planted_truth_and_population(self):
        for case in SCENARIOS:
            rows, groups, users = self.inputs(case)
            truth = build_transitions(case, self.reference)
            self.assertEqual([(e.source.community_id, e.event.value) for e in truth.events],
                             [(group, "stable" if group == "K" else case) for group in sorted(groups["2020-01"])])
            self.assertEqual([(link.source.community_id, link.target.community_id) for link in truth.links],
                             self.expected_links[case])
            sampled = []
            for seed in (11, 12, 13):
                with self.subTest(case=case, seed=seed):
                    expected = dict(expected_reference=self.reference, expected_users_by_month=users)
                    snapshots = sample_snapshots(rows, generator_seed=seed, **expected)
                    self.assertEqual(sample_snapshots(rows, generator_seed=seed, **expected), snapshots)
                    for snapshot in snapshots:
                        self.assertEqual(snapshot.nodes, tuple(sorted(users[snapshot.month])))
                        self.assertTrue(all(e.month == snapshot.month and e.source_user_id < e.target_user_id
                                            and e.source_user_id in snapshot.nodes and e.target_user_id in snapshot.nodes
                                            and e.weight == 1.0 for e in snapshot.edges))
                        pairs = [(e.source_user_id, e.target_user_id) for e in snapshot.edges]
                        self.assertEqual(pairs, sorted(set(pairs)))
                    sampled.append(snapshots)
                    self.assertEqual(build_memberships(case, self.reference), rows)
                    self.assertEqual(build_transitions(case, self.reference), truth)
            # These fixed, nondegenerate fixtures must exercise different graphs.
            self.assertEqual(len(set(sampled)), 3)

    def test_six_case_graphs_ignore_shuffled_rows_and_reversed_month_user_order(self):
        shuffle = random.Random(2026)
        for case in SCENARIOS:
            rows, _, users = self.inputs(case)
            shuffled = list(rows)
            shuffle.shuffle(shuffled)
            shuffled = [Membership(r.reference_id, r.month, "other-" + r.community_id, r.user_id) for r in shuffled]
            reordered = {m: reversed(sorted(users[m])) for m in reversed(tuple(users))}
            with self.subTest(case=case):
                original = sample_snapshots(rows, expected_reference=self.reference, expected_users_by_month=users)
                changed = sample_snapshots(iter(shuffled), expected_reference=self.reference, expected_users_by_month=reordered)
                self.assertEqual(changed, original)

    def test_six_cases_obey_all_four_probability_corners_without_changing_labels(self):
        for case in SCENARIOS:
            rows, groups, users = self.inputs(case)
            truth = build_transitions(case, self.reference)
            for p_in, p_out in ((0, 0), (1, 0), (0, 1), (1, 1)):
                with self.subTest(case=case, p_in=p_in, p_out=p_out):
                    snapshots = sample_snapshots(rows, expected_reference=self.reference, expected_users_by_month=users,
                                                 p_in=p_in, p_out=p_out)
                    for snapshot in snapshots:
                        within = set().union(*(set(combinations(sorted(ids), 2))
                                               for ids in groups[snapshot.month].values()))
                        all_pairs = set(combinations(sorted(users[snapshot.month]), 2))
                        expected = (within if p_in else set()) | (all_pairs - within if p_out else set())
                        self.assertEqual({(e.source_user_id, e.target_user_id) for e in snapshot.edges}, expected)
                        self.assertEqual(snapshot.nodes, tuple(sorted(users[snapshot.month])))
                    self.assertEqual(build_transitions(case, self.reference), truth)


class TinySamplerDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(DIAGNOSTICS.read_text(encoding="utf-8"))
        self.assertEqual(self.fixture["protocol"], "tiny-sampler-diagnostics-v1")
        self.assertEqual(self.fixture["schema_version"], 1)
        self.assertEqual([case["case_id"] for case in self.fixture["cases"]],
                         ["zero-edges", "small-groups", "empty-singleton", "singleton-empty"])

    def sample(self, case):
        reference = "truth-diagnostic-" + case["case_id"]
        rows, users = diagnostic_inputs(case, reference)
        snapshots = sample_snapshots(rows, expected_reference=reference, expected_users_by_month=users,
                                     generator_seed=self.fixture["generator_seed"], p_in=case["p_in"], p_out=case["p_out"])
        return reference, rows, users, snapshots

    def test_tiny_diagnostics_match_declared_counts_including_empty_observed_months(self):
        for case in self.fixture["cases"]:
            with self.subTest(case=case["case_id"]):
                _, _, users, snapshots = self.sample(case)
                self.assertEqual([s.month for s in snapshots], self.fixture["observed_months"])
                for s in snapshots:
                    self.assertEqual(s.nodes, tuple(sorted(users[s.month])))
                    endpoints = {uid for e in s.edges for uid in (e.source_user_id, e.target_user_id)}
                    actual = dict(nodes=len(s.nodes), edges=len(s.edges),
                                  communities=len(case["groups_by_month"][s.month]),
                                  isolates=len(set(s.nodes) - endpoints))
                    self.assertEqual(actual, case["expected_counts"][s.month])
                    pairs = [(e.source_user_id, e.target_user_id) for e in s.edges]
                    self.assertEqual(pairs, [("a", "b")] if case["case_id"] == "small-groups" else [])

    def test_tiny_diagnostic_csv_round_trip_keeps_nodes_memberships_and_header_only_edges(self):
        with tempfile.TemporaryDirectory(prefix="reddit-tiny-csv-") as temporary:
            root = Path(temporary)
            for case in self.fixture["cases"]:
                with self.subTest(case=case["case_id"]):
                    reference, rows, users, snapshots = self.sample(case)
                    folder = root / case["case_id"]
                    folder.mkdir()
                    for s in snapshots:
                        month = folder / s.month
                        month.mkdir()
                        write_nodes(month / "nodes.csv", s.month, s.nodes)
                        write_edges(month / "R.csv", s.edges, expected_month=s.month, expected_users=s.nodes)
                        self.assertEqual(read_nodes(month / "nodes.csv", expected_month=s.month), s.nodes)
                        self.assertEqual(read_edges(month / "R.csv", expected_month=s.month, expected_users=s.nodes), s.edges)
                        if not s.edges:
                            self.assertEqual((month / "R.csv").read_text(encoding="utf-8"), ",".join(EDGE_COLUMNS) + "\n")
                    expected = dict(expected_reference=reference, expected_users_by_month=users)
                    write_memberships(folder / "membership.csv", rows, **expected)
                    self.assertEqual(read_memberships(folder / "membership.csv", **expected), tuple(rows))
