"""Fixed-oracle checks for reporting units, missing values and seed separation."""
import json
import unittest

from reddit_sna.evaluation.detection import _summary_rows


def metric(dataset="dev-stable-easy-g11", *, seed=0, scenario="stable", ami=1.0, status="ok", reason=None,
           coverage=1.0, active=4, scored=4, split="development", difficulty="easy", gamma=1.0):
    return dict(dataset_id=dataset, detector_seed=seed, split=split, scenario=scenario, difficulty=difficulty,
                gamma=gamma, ami=ami, ami_status=status, ami_reason=reason, coverage=coverage,
                n_scored_users=scored, active_nodes=active)


class DetectionSummaryTests(unittest.TestCase):
    def scenario_rows(self, rows):
        return [row for row in _summary_rows(rows) if row["aggregation_level"] == "scenario"]

    def test_ami_mean_is_over_valid_snapshot_rows_not_users_or_missing_defaults(self):
        rows = [metric(ami=1, active=100, scored=100), metric(ami=-0.5, active=4, scored=2, coverage=0.5),
                metric(ami=None, status="degenerate_partition", reason="truth_constant", active=12, scored=12)]
        result, = self.scenario_rows(rows)
        self.assertEqual((result["n_rows"], result["n_datasets"], result["n_ami_valid"], result["n_ami_missing"]), (3, 1, 2, 1))
        self.assertEqual((result["ami_mean"], result["ami_min"], result["ami_max"]), (0.25, -0.5, 1))
        self.assertEqual(result["n_scored_user_observations"], 114)
        self.assertEqual(result["n_active_user_observations"], 116)
        self.assertAlmostEqual(result["coverage_mean"], 5 / 6)
        self.assertEqual(json.loads(result["ami_missing_reasons"]), {"truth_constant": 1})

    def test_each_seed_has_separate_canonical_or_diagnostic_rows(self):
        result = self.scenario_rows([metric(seed=0, ami=1), metric(seed=1, ami=0), metric(seed=2, ami=-0.5)])
        self.assertEqual([(r["detector_seed"], r["seed_role"], r["n_rows"], r["ami_mean"]) for r in result],
                         [(0, "canonical", 1, 1), (1, "diagnostic", 1, 0), (2, "diagnostic", 1, -0.5)])

    def test_all_null_group_keeps_support_and_empty_means(self):
        rows = [metric(ami=None, status="empty_scored", reason="no_scored_users", active=0, scored=0, coverage=None),
                metric(ami=None, status="insufficient_users", reason="fewer_than_2_scored_users", active=1, scored=1),
                metric(ami=None, status="degenerate_partition", reason="truth_constant,prediction_constant")]
        result, = self.scenario_rows(rows)
        self.assertEqual((result["n_ami_valid"], result["n_ami_missing"], result["n_empty_scored"],
                          result["n_insufficient_users"], result["n_degenerate_partition"]), (0, 3, 1, 1, 1))
        self.assertTrue(all(result[key] is None for key in ("ami_mean", "ami_min", "ami_max")))
        self.assertEqual((result["n_coverage_valid"], result["n_coverage_missing"], result["coverage_mean"]), (2, 1, 1))
        self.assertEqual(json.loads(result["ami_missing_reasons"]), {
            "no_scored_users": 1, "fewer_than_2_scored_users": 1, "truth_constant,prediction_constant": 1})

    def test_no_defined_coverage_is_null_but_defined_zero_stays_zero(self):
        empty, = self.scenario_rows([metric(ami=None, status="empty_scored", reason="no_scored_users", active=0, scored=0, coverage=None)])
        self.assertIsNone(empty["coverage_mean"])
        isolated, = self.scenario_rows([metric(ami=None, status="empty_scored", reason="no_scored_users", active=4, scored=0, coverage=0)])
        self.assertEqual(isolated["coverage_mean"], 0)

    def test_overall_is_separate_and_never_combines_splits_difficulties_or_gamma(self):
        rows = [metric(), metric("dev-grow-easy-g11", scenario="grow", ami=0),
                metric("eval-stable-easy-g101", split="evaluation"),
                metric("dev-stable-hard-g11", difficulty="hard"), metric(gamma=2)]
        result = _summary_rows(rows)
        selected = [r for r in result if r["aggregation_level"] == "all_scenarios" and r["split"] == "development"
                    and r["difficulty"] == "easy" and r["gamma"] == 1]
        self.assertEqual(len(selected), 1)
        self.assertEqual((selected[0]["scenario"], selected[0]["n_datasets"], selected[0]["n_rows"], selected[0]["ami_mean"]), ("", 2, 2, 0.5))
        self.assertEqual(result, _summary_rows(list(reversed(rows))))
