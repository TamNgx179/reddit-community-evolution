"""HeTCo v1 gradients, attention normalization and past-only member attributes."""

from pathlib import Path
import sqlite3
import tempfile
import unittest

import numpy as np

from reddit_sna.features.members import MEMBER_FEATURES, member_features
from reddit_sna.models import hetco
from reddit_sna.models.hetco import fit_hetco, predict_hetco


class HeTCoModelTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        self.bags = [rng.normal(size=(n, 3)) for n in (2, 5, 1, 4, 3, 6)]
        self.groups = rng.normal(size=(6, 2))
        self.labels = ["grow", "stable", "grow", "dissolve", "stable", "grow"]

    def test_analytic_gradients_match_finite_differences(self):
        rng = np.random.default_rng(1)
        members, owner, starts = hetco._segments(self.bags[:4])
        target, weights = np.array([0, 1, 5, 1]), np.array([1.0, 0.5, 2.0, 0.5])
        for pooling in ("attention", "mean"):
            params = dict(U=rng.normal(size=(6, 5)), c=rng.normal(size=6))
            if pooling == "attention":
                params.update(W=rng.normal(size=(4, 3)), b=rng.normal(size=4), v=rng.normal(size=4))
            _, grad = hetco._loss_and_grad(params, members, owner, starts, self.groups[:4], target,
                                           weights, pooling, 0.01)
            for key, value in params.items():
                for index in np.ndindex(value.shape):
                    old = value[index]
                    value[index] = old + 1e-6
                    up, _ = hetco._loss_and_grad(params, members, owner, starts, self.groups[:4],
                                                 target, weights, pooling, 0.01)
                    value[index] = old - 1e-6
                    down, _ = hetco._loss_and_grad(params, members, owner, starts, self.groups[:4],
                                                   target, weights, pooling, 0.01)
                    value[index] = old
                    self.assertAlmostEqual((up - down) / 2e-6, grad[key][index], places=5)

    def test_seeded_fit_is_deterministic_and_attention_is_normalized(self):
        first = fit_hetco(self.bags, self.groups, self.labels, 42)
        second = fit_hetco(self.bags, self.groups, self.labels, 42)
        a, proba, attention = predict_hetco(first, self.bags, self.groups)
        self.assertEqual(a, predict_hetco(second, self.bags, self.groups)[0])
        self.assertLess(first["train_loss"][-1], first["train_loss"][0])
        np.testing.assert_allclose(proba.sum(axis=1), 1.0)
        for weights, bag in zip(attention, self.bags):
            self.assertEqual(len(weights), len(bag))
            self.assertAlmostEqual(float(weights.sum()), 1.0)
        self.assertEqual(first["missing_train_classes"], ["shrink", "merge", "split"])

    def test_hierarchical_gradients_match_finite_differences(self):
        rng = np.random.default_rng(2)
        members, owner, starts = hetco._segments(self.bags[:5])
        target = np.array([5, 1, 5, 3, 0])
        weights = (rng.uniform(0.5, 2, 5), rng.uniform(0.5, 2, 3))
        params = dict(U=rng.normal(size=(5, 5)), c=rng.normal(size=5), u=rng.normal(size=5),
                      d=rng.normal(size=1), W=rng.normal(size=(4, 3)), b=rng.normal(size=4), v=rng.normal(size=4))
        args = (members, owner, starts, self.groups[:5], target, weights, "attention", 0.01, "hierarchical")
        _, grad = hetco._loss_and_grad(params, *args)
        for key, value in params.items():
            for index in np.ndindex(value.shape):
                old = value[index]
                value[index] = old + 1e-6
                up, _ = hetco._loss_and_grad(params, *args)
                value[index] = old - 1e-6
                down, _ = hetco._loss_and_grad(params, *args)
                value[index] = old
                self.assertAlmostEqual((up - down) / 2e-6, grad[key][index], places=5)

    def test_hierarchical_probabilities_sum_to_one(self):
        fitted = fit_hetco(self.bags, self.groups, self.labels, 42, head="hierarchical", class_weight="sqrt")
        _, proba, _ = predict_hetco(fitted, self.bags, self.groups)
        np.testing.assert_allclose(proba.sum(axis=1), 1.0)

    def test_class_weight_schemes(self):
        target = np.array([0, 0, 0, 1])
        np.testing.assert_allclose(hetco.class_weights(target, 6, "balanced"), [2 / 3] * 3 + [2.0])
        np.testing.assert_allclose(hetco.class_weights(target, 6, "sqrt"), np.sqrt([2 / 3] * 3 + [2.0]))
        np.testing.assert_allclose(hetco.class_weights(target, 6, "none"), 1.0)
        with self.assertRaises(ValueError):
            hetco.class_weights(target, 6, "log")

    def test_mean_pooling_gives_uniform_weights(self):
        fitted = fit_hetco(self.bags, self.groups, self.labels, 42, pooling="mean")
        for weights, bag in zip(predict_hetco(fitted, self.bags, self.groups)[2], self.bags):
            np.testing.assert_allclose(weights, 1.0 / len(bag))

    def test_rejects_empty_community_and_unknown_pooling(self):
        with self.assertRaises(ValueError):
            fit_hetco([np.zeros((0, 3))], [[0.0, 0.0]], ["grow"], 42)
        with self.assertRaises(ValueError):
            fit_hetco(self.bags, self.groups, self.labels, 42, pooling="max")


class MemberFeatureTests(unittest.TestCase):
    def _build(self, root, extra_future=False):
        db = sqlite3.connect(root / "normalized.sqlite")
        db.execute("CREATE TABLE records(id TEXT PRIMARY KEY, user_id TEXT, root TEXT, parent TEXT,"
                   " timestamp REAL, month TEXT, kind TEXT, corpus TEXT)")
        db.execute("CREATE TABLE provenance(key TEXT PRIMARY KEY, value TEXT)")
        rows = [("1", "a", "r", None, 0, "2015-01", "c", "X"), ("2", "a", "r", None, 0, "2015-02", "c", "Y"),
                ("3", "b", "r", None, 0, "2015-02", "c", "X"), ("4", "b", "r", None, 0, "2015-02", "c", "Y")]
        if extra_future:
            rows += [("5", "a", "r", None, 0, "2015-03", "c", "X"), ("6", "b", "r", None, 0, "2015-03", "c", "X")]
        db.executemany("INSERT INTO records VALUES(?,?,?,?,?,?,?,?)", rows)
        db.commit()
        db.close()
        for month, edges in (("2015-01", []), ("2015-02", [("a", "b", 3), ("b", "c", 1)])):
            (root / month).mkdir(parents=True)
            (root / month / "R.csv").write_text(
                "month,source_user_id,target_user_id,weight\n"
                + "".join(f"{month},{s},{t},{w}\n" for s, t, w in edges), encoding="utf-8")

    def test_values_use_only_current_and_earlier_months(self):
        groups = {"2015-01": {"g": {"a"}}, "2015-02": {"g": {"a", "b"}, "h": {"c"}}}
        results = []
        for future in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._build(root, future)
                results.append(member_features(root / "normalized.sqlite", root, ["2015-01", "2015-02"], groups))
        self.assertEqual(results[0], results[1])
        a, b = results[0][("2015-02", "g")]
        row = dict(zip(MEMBER_FEATURES, a))
        self.assertAlmostEqual(row["internal_share"], 1.0)
        self.assertEqual(row["previous_active"], 1.0)
        self.assertAlmostEqual(row["log_tenure"], np.log1p(2))
        self.assertAlmostEqual(dict(zip(MEMBER_FEATURES, b))["internal_share"], 0.75)
        self.assertEqual(dict(zip(MEMBER_FEATURES, b))["corpus_count"], 2.0)


if __name__ == "__main__":
    unittest.main()
