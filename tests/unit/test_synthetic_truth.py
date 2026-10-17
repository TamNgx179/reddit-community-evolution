"""Behavior checks for planted memberships and algorithm-independent truth."""

from collections import defaultdict
import unittest
from unittest.mock import patch

from reddit_sna.benchmarks.scenarios import TruthEvent, build_memberships, build_transitions
from reddit_sna.contracts import Event, SampleKey


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


class PlantedTransitionTests(unittest.TestCase):
    def test_stable_labels_the_renamed_main_group_and_the_background(self):
        truth = build_transitions("stable", "truth-stable")
        self.assertEqual(
            [(row.source.community_id, row.event) for row in truth.events],
            [("A", Event.STABLE), ("K", Event.STABLE)],
        )
        self.assertEqual(
            [(row.source.community_id, row.target.community_id) for row in truth.links],
            [("A", "C"), ("K", "K")],
        )

    def test_grow_labels_only_the_main_group_as_grow(self):
        truth = build_transitions("grow", "truth-grow")
        self.assertEqual(
            [(row.source.community_id, row.event) for row in truth.events],
            [("A", Event.GROW), ("K", Event.STABLE)],
        )
        self.assertEqual(
            [(row.source.community_id, row.target.community_id) for row in truth.links],
            [("A", "C"), ("K", "K")],
        )

    def test_each_source_has_one_event_and_links_to_existing_next_month_groups(self):
        for scenario in ("stable", "grow"):
            with self.subTest(scenario=scenario):
                reference = f"truth-{scenario}"
                memberships = build_memberships(scenario, reference)
                groups = {
                    SampleKey(row.reference_id, row.month, row.community_id)
                    for row in memberships
                }
                sources = {key for key in groups if key.feature_month == "2020-01"}
                truth = build_transitions(scenario, reference)
                self.assertEqual(len(truth.events), len(sources))
                self.assertEqual({row.source for row in truth.events}, sources)
                self.assertEqual({row.source for row in truth.links}, sources)
                self.assertEqual(len(set(truth.links)), len(truth.links))
                for event in truth.events:
                    self.assertEqual(event.source.reference_id, reference)
                    self.assertEqual(event.target_month, "2020-02")
                for link in truth.links:
                    self.assertIn(link.source, groups)
                    self.assertIn(link.target, groups)
                    self.assertEqual(link.target.reference_id, reference)
                    self.assertEqual(link.target.feature_month, "2020-02")

    def test_final_month_is_not_labeled_or_mistaken_for_dissolve(self):
        for scenario in ("stable", "grow"):
            with self.subTest(scenario=scenario):
                truth = build_transitions(scenario, "truth-final")
                self.assertEqual({row.source.feature_month for row in truth.events}, {"2020-01"})
                self.assertEqual({row.source.feature_month for row in truth.links}, {"2020-01"})
                self.assertNotIn(Event.DISSOLVE, [row.event for row in truth.events])

    def test_missing_observed_successor_produces_neither_events_nor_links(self):
        for scenario in ("stable", "grow"):
            for observed in (("2020-01",), ("2020-02",)):
                with self.subTest(scenario=scenario, observed=observed):
                    truth = build_transitions(scenario, "truth-partial", observed_months=observed)
                    self.assertEqual(truth.events, ())
                    self.assertEqual(truth.links, ())

    def test_explicit_observation_order_does_not_change_truth(self):
        expected = build_transitions("grow", "truth-repeat")
        observed = (month for month in ("2020-02", "2020-01"))
        actual = build_transitions("grow", "truth-repeat", observed_months=observed)
        self.assertEqual(actual, expected)
        self.assertEqual(build_transitions("grow", "truth-repeat"), expected)

    def test_custom_start_month_carries_reference_across_year_boundary(self):
        truth = build_transitions("grow", "truth-year", start_month="2020-12")
        for row in truth.events:
            self.assertEqual(row.source.reference_id, "truth-year")
            self.assertEqual(row.source.feature_month, "2020-12")
            self.assertEqual(row.target_month, "2021-01")
        for row in truth.links:
            self.assertEqual(row.target.feature_month, "2021-01")
        partial = build_transitions(
            "grow", "truth-year", start_month="2020-12", observed_months=["2020-12"],
        )
        self.assertEqual(partial.events, ())
        self.assertEqual(partial.links, ())

    def test_truth_is_declared_without_inspecting_memberships(self):
        with patch(
            "reddit_sna.benchmarks.scenarios.build_memberships",
            side_effect=AssertionError("truth must not classify membership overlap"),
        ):
            truth = build_transitions("grow", "truth-independent")
        self.assertEqual([row.event for row in truth.events], [Event.GROW, Event.STABLE])

    def test_invalid_observation_lists_are_rejected(self):
        for observed in (
            [], "2020-01", b"2020-01", 1, ["2020-01", "2020-01"],
            ["2020-03"], ["2020-01", "2020-03"], ["2020-1"], [None],
        ):
            with self.subTest(observed=observed), self.assertRaises(ValueError):
                build_transitions("stable", "truth-invalid", observed_months=observed)

    def test_invalid_scenario_reference_or_start_month_cannot_produce_truth(self):
        for scenario in ("merge", "shrink", "", None):
            with self.subTest(scenario=scenario), self.assertRaises(ValueError):
                build_transitions(scenario, "truth-invalid")
        for reference in ("", " ", None):
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                build_transitions("stable", reference)
        for month in ("2020-00", "2020-13", "2020-1", "2020-01-01", None):
            with self.subTest(month=month), self.assertRaises(ValueError):
                build_transitions("stable", "truth-invalid", start_month=month)

    def test_event_record_rejects_nonconsecutive_months_and_invalid_labels(self):
        source = SampleKey("truth-record", "2020-12", "A")
        self.assertEqual(TruthEvent(source, "2021-01", Event.GROW).source, source)
        for month in ("2020-12", "2021-02", "2021-1", None):
            with self.subTest(month=month), self.assertRaises(ValueError):
                TruthEvent(source, month, Event.GROW)
        for label in ("grow", "made-up-label", None):
            with self.subTest(label=label), self.assertRaises(ValueError):
                TruthEvent(source, "2021-01", label)
        with self.assertRaises(ValueError):
            TruthEvent(None, "2021-01", Event.GROW)
