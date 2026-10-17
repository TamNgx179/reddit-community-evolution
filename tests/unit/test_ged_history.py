"""Hand-calculated GED inclusion and lineage history, independent of Reddit."""

import unittest
import random

from reddit_sna.contracts import Event, SnapshotEdge
from reddit_sna.tracking.ged import importance, inclusion, passes, transitions
from reddit_sna.features.history import history_features


def uniform(groups):
    return {cid: dict.fromkeys(users, 1.0) for cid, users in groups.items()}


class GedTests(unittest.TestCase):
    def test_inclusive_numeric_boundary_and_weight_rescaling(self):
        self.assertTrue(passes(0.5 - 1e-16, 0.5))
        self.assertFalse(passes(0.5 - 1e-8, 0.5))
        source = {"s": {1, 2, 3, 4}}
        target = {"t": {1, 2, 5, 6}}
        before = transitions(source, target, uniform(source), uniform(target), alpha=0.25, beta=0.25)
        scaled_source = {"s": dict.fromkeys(source["s"], 0.1)}
        scaled_target = {"t": dict.fromkeys(target["t"], 100.0)}
        after = transitions(source, target, scaled_source, scaled_target, alpha=0.25, beta=0.25)
        self.assertEqual(before[1], after[1])
        self.assertEqual(before[3][0]["accepted"], after[3][0]["accepted"])
    def test_sparse_pair_scan_matches_independent_full_inclusion_scan(self):
        rng = random.Random(99)
        for _ in range(50):
            source, target = {}, {}
            for user in range(40):
                if rng.random() < 0.8:
                    source.setdefault(str(rng.randrange(5)), set()).add(user)
                if rng.random() < 0.8:
                    target.setdefault(str(rng.randrange(5)), set()).add(user)
            sw = {cid: {u: rng.uniform(1, 10) for u in members} for cid, members in source.items()}
            tw = {cid: {u: rng.uniform(1, 10) for u in members} for cid, members in target.items()}
            pairs = transitions(source, target, sw, tw)[3]
            actual = {(r["source_community_id"], r["target_community_id"]): r for r in pairs}
            for sid, members in source.items():
                for tid, others in target.items():
                    if members & others:
                        self.assertAlmostEqual(actual[sid, tid]["inclusion_forward"], inclusion(members, others, sw[sid]))
                        self.assertAlmostEqual(actual[sid, tid]["inclusion_backward"], inclusion(others, members, tw[tid]))
                    else:
                        self.assertNotIn((sid, tid), actual)

    def track(self, source, target, **kwargs):
        return transitions(source, target, uniform(source), uniform(target), **kwargs)

    def test_asymmetric_inclusion_and_member_importance(self):
        self.assertAlmostEqual(inclusion({"a", "b"}, {"a"}, {"a": 9, "b": 1}), 0.45)
        self.assertAlmostEqual(inclusion({"a", "b"}, {"b"}, {"a": 9, "b": 1}), 0.05)
        self.assertEqual(inclusion({"a"}, {"a", "b"}, {"a": 1}), 1)
        self.assertEqual(inclusion({"a"}, {"b"}, {"a": 1}), 0)
        for weights in ({}, {"a": 0}, {"a": float("nan")}, {"a": float("inf")}):
            with self.assertRaises(ValueError):
                inclusion({"a"}, {"a"}, weights)

    def test_internal_strength_ignores_boundary_and_handles_isolate(self):
        groups = {"x": {"a", "b", "c"}, "y": {"d"}}
        edges = [SnapshotEdge("2015-01", "a", "b", 3), SnapshotEdge("2015-01", "b", "d", 10)]
        self.assertEqual(importance(groups, edges), {"x": {"a": 3, "b": 3, "c": 1}, "y": {"d": 1}})

    def test_all_six_unambiguous_events(self):
        cases = [({"s": {1, 2}}, {"t": {1, 2}}, Event.STABLE),
                 ({"s": {1, 2}}, {"t": {1, 2, 3}}, Event.GROW),
                 ({"s": {1, 2, 3}}, {"t": {1, 2}}, Event.SHRINK),
                 ({"s": {1, 2}}, {"t": {8, 9}}, Event.DISSOLVE),
                 ({"s": {1, 2, 3, 4}}, {"t": {1, 2}, "u": {3, 4}}, Event.SPLIT),
                 ({"s": {1, 2}, "u": {3, 4}}, {"t": {1, 2, 3, 4}}, Event.MERGE)]
        for source, target, expected in cases:
            with self.subTest(event=expected):
                self.assertEqual(self.track(source, target)[1]["s"], expected)

    def test_weak_overlap_is_excluded_not_dissolved(self):
        result = self.track({"s": {1, 2, 3, 4}}, {"t": {1, 2, 5, 6}})
        self.assertIsNone(result[1]["s"])
        self.assertEqual(result[2]["s"], "weak_overlap_unresolved")
        self.assertEqual(result[3][0]["inclusion_forward"], 0.25)
        self.assertEqual(result[3][0]["accepted"], 0)

    def test_many_to_many_is_explicitly_ambiguous(self):
        result = self.track({"s": {1, 2}, "u": {3, 4}}, {"t": {1, 3}, "v": {2, 4}}, alpha=0.25, beta=0.25)
        self.assertEqual(set(result[1].values()), {None})
        self.assertEqual(set(result[2].values()), {"many_to_many_unresolved"})

    def test_threshold_boundary_empty_and_invalid_options(self):
        self.assertEqual(self.track({"s": {1, 2}}, {})[1]["s"], Event.DISSOLVE)
        self.assertEqual(self.track({}, {"t": {1}})[1], {})
        self.assertEqual(self.track({"s": {1, 2}}, {"t": {1}}, alpha=0.25)[3][0]["accepted"], 1)
        for kwargs in ({"alpha": 0}, {"beta": float("nan")}, {"dissolve": 0.6}, {"alpha": 2}):
            with self.assertRaises(ValueError):
                self.track({}, {}, **kwargs)
        with self.assertRaises(ValueError):
            transitions({"s": {1}}, {}, {}, {})


class HistoryTests(unittest.TestCase):
    def test_first_observation_missing_flag(self):
        row = history_features({"a": {1, 2}})["a"]
        self.assertEqual(row["community_age"], 1)
        self.assertEqual(row["history_missing"], 1)
        self.assertEqual(row["past_growth"], 0)

    def test_one_to_one_history_uses_previous_members_only(self):
        row = history_features({"a": {2, 3, 4}}, {"old": {1, 2}},
                               {"old": [("a", 0.8)]}, {"old": 4})["a"]
        self.assertEqual(row["community_age"], 5)
        self.assertEqual(row["past_growth"], 0.5)
        self.assertEqual(row["past_retention"], 0.5)
        self.assertAlmostEqual(row["inflow_fraction"], 2/3)
        self.assertEqual(row["outflow_fraction"], 0.5)

    def test_merge_and_split_reset_age_and_union_members(self):
        rows = history_features({"a": {1, 2, 3}}, {"s": {1, 2}, "u": {3, 4}},
                                {"s": [("a", 1)], "u": [("a", 1)]}, {"s": 8, "u": 9})
        self.assertEqual(rows["a"]["community_age"], 1)
        self.assertEqual(rows["a"]["predecessor_count"], 2)
        self.assertEqual(rows["a"]["past_retention"], 0.75)
        rows = history_features({"a": {1}, "b": {2}}, {"s": {1, 2}},
                                {"s": [("a", 1), ("b", 1)]}, {"s": 8})
        self.assertEqual([rows[c]["community_age"] for c in ("a", "b")], [1, 1])
