"""Fallback event semantics and temporal leakage regression checks."""

import unittest
from copy import deepcopy
import random

from reddit_sna.contracts import Event, SnapshotEdge
from reddit_sna.features.community import FEATURES, snapshot_features
from reddit_sna.pipelines.forecast import evaluate
from reddit_sna.tracking.jaccard import transitions


class ForecastTests(unittest.TestCase):
    def test_jaccard_threshold_boundary_and_birth(self):
        source, target = {"a": {1, 2}}, {"b": {1, 3}, "born": {9}}
        self.assertEqual(transitions(source, target, 1 / 3)[0]["a"], [("b", 1 / 3)])
        self.assertEqual(transitions(source, target, 0.334)[1]["a"], Event.DISSOLVE)
        self.assertEqual(set(transitions(source, target)[1]), {"a"})
        self.assertEqual(transitions({}, {"born": {9}}), ({}, {}))

    def test_invalid_partitions_rejected_on_both_sides(self):
        for bad in ({"a": set()}, {"a": {1}, "b": {1, 2}}):
            for source, target in ((bad, {}), ({}, bad)):
                with self.assertRaises(ValueError):
                    transitions(source, target)

    def test_random_partitions_match_independent_pairwise_oracle(self):
        rng = random.Random(17)
        for _ in range(100):
            groups = []
            for _side in range(2):
                partition = {}
                for user in range(30):
                    if rng.random() < 0.8:
                        partition.setdefault(str(rng.randrange(6)), set()).add(user)
                groups.append(partition)
            source, target = groups
            expected = {(s, t): len(a & b) / len(a | b)
                        for s, a in source.items() for t, b in target.items()
                        if len(a & b) / len(a | b) >= 0.25}
            links, events = transitions(source, target)
            self.assertEqual({(s, t): score for s, pairs in links.items() for t, score in pairs}, expected)
            for sid, event in events.items():
                successors = [t for s, t in expected if s == sid]
                if not successors:
                    correct = Event.DISSOLVE
                elif len(successors) > 1:
                    correct = Event.SPLIT
                elif sum(t == successors[0] for s, t in expected) > 1:
                    correct = Event.MERGE
                else:
                    difference = len(target[successors[0]]) - len(source[sid])
                    correct = Event.GROW if difference > 0 else Event.SHRINK if difference < 0 else Event.STABLE
                self.assertEqual(event, correct)
            # Renaming local community IDs and reversing insertion order preserve events.
            renamed = [{f"x{k}": v for k, v in reversed(list(g.items()))} for g in groups]
            self.assertEqual(transitions(*renamed)[1], {f"x{k}": v for k, v in events.items()})

    def test_features_empty_singleton_and_invalid_edges(self):
        self.assertEqual(snapshot_features({}, []), {})
        self.assertEqual(snapshot_features({"a": {"1"}}, [])["a"]["density"], 0)
        valid = SnapshotEdge("2015-01", "1", "2", 1)
        cases = [({"a": set()}, []), ({"a": {"1"}, "b": {"1"}}, []),
                 ({"a": {"1"}}, [valid]),
                 ({"a": {"1", "2"}}, [valid, SnapshotEdge("2015-01", "2", "1", 1)]),
                 ({"a": {"1", "2", "3"}}, [valid, SnapshotEdge("2015-02", "2", "3", 1)])]
        for groups, edges in cases:
            with self.subTest(groups=groups, edges=edges), self.assertRaises(ValueError):
                snapshot_features(groups, edges)

    def test_feature_invariance_under_user_renaming_and_edge_order(self):
        groups = {"a": {"1", "2"}, "b": {"3"}}
        edges = [SnapshotEdge("2015-01", "1", "2", 2), SnapshotEdge("2015-01", "2", "3", 3)]
        renamed = {k: {"u" + u for u in users} for k, users in groups.items()}
        reverse = [SnapshotEdge(e.month, "u" + e.target_user_id, "u" + e.source_user_id, e.weight)
                   for e in reversed(edges)]
        self.assertEqual(snapshot_features(groups, edges), snapshot_features(renamed, reverse))

    def test_invalid_samples_rejected(self):
        base = [self.sample("2015-01", "2015-02", "stable"),
                self.sample("2015-02", "2015-03", "grow")]
        mutations = [("label_month", "2015-04"), ("label", "unknown"),
                     ("reference_id", "different"), ("size", float("nan")),
                     ("size", float("inf")), ("size", "2")]
        for field, value in mutations:
            rows = deepcopy(base)
            rows[1][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                evaluate(rows, "2015-03")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            evaluate(base + [base[0]], "2015-03")
        for split in ("2015-01", "2016-01", "2015-13", "2015-3"):
            with self.assertRaises(ValueError):
                evaluate(base, split)
        for seed in (-1, 2**32, True):
            with self.assertRaises(ValueError):
                evaluate(base, "2015-03", seed)

    def test_scaler_fit_and_coefficients_ignore_heldout_values_and_labels(self):
        rows = [self.sample("2014-12", "2015-01", "stable", 2),
                self.sample("2015-01", "2015-02", "grow", 4),
                self.sample("2015-02", "2015-03", "shrink", 6)]
        models = {}
        evaluate(rows, "2015-03", model_store=models)
        old = models["logistic_regression"]
        self.assertEqual(old.named_steps["standardscaler"].mean_[0], 3)
        rows[-1].update(size=1e12, label="split")
        new_models = {}
        evaluate(rows, "2015-03", model_store=new_models)
        new = new_models["logistic_regression"]
        self.assertEqual(old.named_steps["standardscaler"].mean_.tolist(),
                         new.named_steps["standardscaler"].mean_.tolist())
        self.assertEqual(old.named_steps["logisticregression"].coef_.tolist(),
                         new.named_steps["logisticregression"].coef_.tolist())

    def test_metrics_match_independent_confusion_counts_and_repeatability(self):
        rows = [self.sample("2015-01", "2015-02", "stable"),
                self.sample("2015-02", "2015-03", "grow")]
        first = evaluate(rows, "2015-03")
        self.assertEqual(first, evaluate(list(reversed(rows)), "2015-03"))
        for result in first[1]["models"].values():
            self.assertEqual(sum(map(sum, result["confusion_matrix"])), 1)
            self.assertEqual(result["confusion_matrix"][1][0], 1)
            self.assertEqual(result["macro_f1"], 0)

    def test_six_events_and_ambiguous_precedence(self):
        cases = [({"a": {1, 2}}, {"b": {1, 2}}, Event.STABLE),
                 ({"a": {1, 2}}, {"b": {1, 2, 3}}, Event.GROW),
                 ({"a": {1, 2, 3}}, {"b": {1, 2}}, Event.SHRINK),
                 ({"a": {1, 2}}, {"b": {3, 4}}, Event.DISSOLVE),
                 ({"a": {1, 2, 3, 4}}, {"b": {1, 2}, "c": {3, 4}}, Event.SPLIT),
                 ({"a": {1, 2}, "c": {3, 4}}, {"b": {1, 2, 3, 4}}, Event.MERGE)]
        for source, target, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(transitions(source, target)[1]["a"], expected)
        self.assertEqual(transitions({"a": {1, 2}, "b": {3, 4}},
                                     {"c": {1, 3}, "d": {2, 4}})[1]["a"], Event.SPLIT)

    def test_threshold_and_empty_snapshot(self):
        self.assertEqual(transitions({"a": {1}}, {})[1]["a"], Event.DISSOLVE)
        self.assertEqual(transitions({}, {})[1], {})
        for threshold in (0, 1.1, float("nan")):
            with self.assertRaises(ValueError):
                transitions({}, {}, threshold)

    def test_features_use_only_current_graph(self):
        row = snapshot_features({"a": {"1", "2"}, "b": {"3"}},
                                [SnapshotEdge("2015-01", "1", "2", 2),
                                 SnapshotEdge("2015-01", "2", "3", 3)])["a"]
        self.assertEqual(row, dict(size=2, internal_edges=1, internal_weight=2,
                                   boundary_weight=3, density=1))

    def sample(self, feature_month, label_month, label, size=2):
        return dict(reference_id="ref", community_id="a", feature_month=feature_month,
                    label_month=label_month, label=label,
                    **{f: size if f == "size" else 0 for f in FEATURES})

    def test_temporal_split_and_single_class_fallback(self):
        rows = [self.sample("2015-01", "2015-02", "stable"),
                self.sample("2015-02", "2015-03", "grow", 100)]
        predictions, metrics = evaluate(rows, "2015-03")
        self.assertEqual(metrics["train_samples"], 1)
        self.assertEqual({p["y_pred"] for p in predictions}, {"stable"})
        self.assertEqual({p["label_month"] for p in predictions}, {"2015-03"})
        self.assertIn("logistic_regression_fallback_majority", metrics["models"])
        self.assertEqual(len(metrics["models"]["majority"]["confusion_matrix"]), 6)
        with self.assertRaises(ValueError):
            evaluate(rows, "2015-02")

    def test_future_changes_cannot_change_training(self):
        rows = [self.sample("2015-01", "2015-02", "stable"),
                self.sample("2015-02", "2015-03", "grow", 3),
                self.sample("2015-03", "2015-04", "shrink", 2)]
        before, _ = evaluate(rows, "2015-04")
        rows[-1]["label"] = "dissolve"
        after, _ = evaluate(rows, "2015-04")
        self.assertEqual([r["y_pred"] for r in before], [r["y_pred"] for r in after])
