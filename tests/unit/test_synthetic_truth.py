"""Behavior checks for planted memberships, without graphs or tracker labels."""

from collections import defaultdict
import unittest

from reddit_sna.benchmarks.scenarios import build_memberships


def partitions(memberships):
    result = defaultdict(lambda: defaultdict(set))
    for row in memberships:
        result[row.month][row.community_id].add(row.user_id)
    return result


class PlantedMembershipTests(unittest.TestCase):
    def test_stable_preserves_members_under_a_different_community_name(self):
        groups = partitions(build_memberships("stable", "truth-stable"))
        source, target = groups["2020-01"], groups["2020-02"]
        self.assertEqual(set(source), {"A", "K"})
        self.assertEqual(set(target), {"C", "K"})
        self.assertEqual(len(source["A"]), 12)
        self.assertEqual(source["A"], target["C"])

    def test_grow_keeps_all_original_members_and_adds_six_new_users(self):
        groups = partitions(build_memberships("grow", "truth-grow"))
        source, target = groups["2020-01"], groups["2020-02"]
        self.assertEqual(set(source), {"A", "K"})
        self.assertEqual(set(target), {"C", "K"})
        self.assertEqual(len(source["A"]), 12)
        self.assertEqual(len(target["C"]), 18)
        self.assertTrue(source["A"] < target["C"])
        newcomers = target["C"] - source["A"]
        self.assertEqual(len(newcomers), 6)
        self.assertTrue(newcomers.isdisjoint(source["A"] | source["K"]))

    def test_background_is_stable_and_disjoint_from_both_main_groups(self):
        for scenario in ("stable", "grow"):
            with self.subTest(scenario=scenario):
                groups = partitions(build_memberships(scenario, "truth-background"))
                source, target = groups["2020-01"], groups["2020-02"]
                self.assertEqual(len(source["K"]), 12)
                self.assertEqual(source["K"], target["K"])
                self.assertTrue(source["K"].isdisjoint(source["A"]))
                self.assertTrue(target["K"].isdisjoint(target["C"]))

    def test_each_user_has_one_membership_per_month_in_the_requested_reference(self):
        for scenario, target_population in (("stable", 24), ("grow", 30)):
            with self.subTest(scenario=scenario):
                reference = f"truth-{scenario}-dataset-11"
                rows = build_memberships(scenario, reference)
                keys = {(row.month, row.user_id) for row in rows}
                self.assertEqual(len(keys), len(rows))
                self.assertEqual({row.reference_id for row in rows}, {reference})
                self.assertEqual({row.month for row in rows}, {"2020-01", "2020-02"})
                self.assertEqual(sum(row.month == "2020-01" for row in rows), 24)
                self.assertEqual(sum(row.month == "2020-02" for row in rows), target_population)

    def test_results_are_repeatable_and_have_stable_record_order(self):
        for scenario in ("stable", "grow"):
            with self.subTest(scenario=scenario):
                first = build_memberships(scenario, "truth-repeat")
                build_memberships("grow", "another-dataset")
                self.assertEqual(first, build_memberships(scenario, "truth-repeat"))
                keys = [(row.month, row.community_id, row.user_id) for row in first]
                self.assertEqual(keys, sorted(keys))

    def test_custom_start_month_uses_the_next_month_across_year_boundary(self):
        rows = build_memberships("grow", "truth-year", start_month="2020-12")
        groups = partitions(rows)
        self.assertEqual(set(groups), {"2020-12", "2021-01"})
        self.assertTrue(groups["2020-12"]["A"] < groups["2021-01"]["C"])

    def test_unsupported_scenario_is_rejected_instead_of_fabricating_memberships(self):
        for scenario in ("merge", "shrink", "", None):
            with self.subTest(scenario=scenario), self.assertRaises(ValueError):
                build_memberships(scenario, "truth-invalid")

    def test_invalid_reference_and_start_month_are_rejected(self):
        for reference in ("", " ", None):
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                build_memberships("stable", reference)
        for month in ("2020-00", "2020-13", "2020-1", "2020-01-01", None):
            with self.subTest(month=month), self.assertRaises(ValueError):
                build_memberships("stable", "truth-invalid", start_month=month)
