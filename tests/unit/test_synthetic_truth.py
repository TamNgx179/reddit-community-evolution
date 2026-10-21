"""Behavior checks for planted memberships and algorithm-independent truth."""

from collections import defaultdict
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from reddit_sna.benchmarks.io import read_memberships, write_memberships, write_nodes
from reddit_sna.benchmarks.scenarios import SCENARIOS, TruthEvent, build_memberships, build_transitions
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
        for scenario in ("forming", "unknown", "", None):
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
        for scenario in ("forming", "unknown", "", None):
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


class SixEventScenarioTests(unittest.TestCase):
    def setUp(self):
        self.reference = "truth-six-events"
        self.main12 = {f"u{i:03d}" for i in range(1, 13)}
        self.other12 = {f"u{i:03d}" for i in range(13, 25)}
        self.main18 = {f"u{i:03d}" for i in range(1, 19)}
        self.background = {f"u{i:03d}" for i in range(101, 113)}
        self.expected = {
            "stable": ({"A": self.main12}, {"C": self.main12}),
            "grow": ({"A": self.main12}, {"C": self.main18}),
            "shrink": ({"A": self.main18}, {"C": self.main12}),
            "merge": ({"A": self.main12, "B": self.other12}, {"C": self.main12 | self.other12}),
            "split": ({"A": self.main12 | self.other12}, {"B": self.main12, "C": self.other12}),
            "dissolve": ({"A": self.main12}, {}),
        }

    def test_all_six_memberships_match_independent_exact_populations(self):
        self.assertEqual(SCENARIOS, ("stable", "grow", "shrink", "merge", "split", "dissolve"))
        for scenario, (source, target) in self.expected.items():
            with self.subTest(scenario=scenario):
                rows = build_memberships(scenario, self.reference)
                expected = {
                    "2020-01": dict(source, K=self.background),
                    "2020-02": dict(target, K=self.background),
                }
                self.assertEqual(partitions(rows), expected)
                self.assertEqual(len({(row.month, row.user_id) for row in rows}), len(rows))
                self.assertEqual({row.reference_id for row in rows}, {self.reference})
                # K must stay separate from every main group in both months.
                for groups in expected.values():
                    self.assertTrue(all(users.isdisjoint(self.background)
                                        for key, users in groups.items() if key != "K"))

    def test_every_source_has_one_expected_event_and_exact_target_links(self):
        expected = {
            "stable": ({"A": Event.STABLE}, (("A", "C"),)),
            "grow": ({"A": Event.GROW}, (("A", "C"),)),
            "shrink": ({"A": Event.SHRINK}, (("A", "C"),)),
            "merge": ({"A": Event.MERGE, "B": Event.MERGE}, (("A", "C"), ("B", "C"))),
            "split": ({"A": Event.SPLIT}, (("A", "B"), ("A", "C"))),
            "dissolve": ({"A": Event.DISSOLVE}, ()),
        }
        for scenario, (main_labels, main_links) in expected.items():
            with self.subTest(scenario=scenario):
                groups = partitions(build_memberships(scenario, self.reference))
                truth = build_transitions(scenario, self.reference)
                labels = dict(main_labels, K=Event.STABLE)
                self.assertEqual(len(truth.events), len(labels))
                self.assertEqual({event.source.community_id: event.event for event in truth.events}, labels)
                self.assertEqual({event.source.community_id for event in truth.events}, set(groups["2020-01"]))
                self.assertEqual([(link.source.community_id, link.target.community_id) for link in truth.links],
                                 list(main_links) + [("K", "K")])
                self.assertEqual(len(set(truth.links)), len(truth.links))
                for event in truth.events:
                    self.assertEqual(event.source.reference_id, self.reference)
                    self.assertEqual(event.source.feature_month, "2020-01")
                    self.assertEqual(event.target_month, "2020-02")
                for link in truth.links:
                    self.assertIsNotNone(link.target)
                    self.assertEqual(link.target.reference_id, self.reference)
                    self.assertEqual(link.target.feature_month, "2020-02")
                    self.assertIn(link.target.community_id, groups["2020-02"])

    def test_merge_and_split_conserve_members_and_shrink_dissolve_remove_them(self):
        merged = partitions(build_memberships("merge", self.reference))
        self.assertTrue(merged["2020-01"]["A"].isdisjoint(merged["2020-01"]["B"]))
        self.assertEqual(merged["2020-02"]["C"], merged["2020-01"]["A"] | merged["2020-01"]["B"])
        split = partitions(build_memberships("split", self.reference))
        self.assertTrue(split["2020-02"]["B"].isdisjoint(split["2020-02"]["C"]))
        self.assertEqual(split["2020-01"]["A"], split["2020-02"]["B"] | split["2020-02"]["C"])
        shrunk = partitions(build_memberships("shrink", self.reference))
        removed = shrunk["2020-01"]["A"] - shrunk["2020-02"]["C"]
        self.assertEqual(len(removed), 6)
        self.assertTrue(removed.isdisjoint(set().union(*shrunk["2020-02"].values())))
        dissolved = partitions(build_memberships("dissolve", self.reference))
        self.assertEqual(set(dissolved["2020-02"]), {"K"})
        self.assertTrue(dissolved["2020-01"]["A"].isdisjoint(dissolved["2020-02"]["K"]))

    def test_no_scenario_labels_the_final_month_or_unobserved_successor(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                full = build_transitions(scenario, self.reference)
                self.assertEqual({event.source.feature_month for event in full.events}, {"2020-01"})
                for month in ("2020-01", "2020-02"):
                    partial = build_transitions(scenario, self.reference, observed_months=[month])
                    self.assertEqual(partial.events, ())
                    self.assertEqual(partial.links, ())

    def test_all_scenarios_repeat_in_canonical_order_and_cross_year_boundary(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                rows = build_memberships(scenario, self.reference, start_month="2020-12")
                truth = build_transitions(scenario, self.reference, start_month="2020-12")
                build_memberships("grow", "another-reference")
                self.assertEqual(build_memberships(scenario, self.reference, start_month="2020-12"), rows)
                self.assertEqual(build_transitions(scenario, self.reference, start_month="2020-12"), truth)
                self.assertEqual({row.month for row in rows}, {"2020-12", "2021-01"})
                keys = [(row.month, row.community_id, row.user_id) for row in rows]
                self.assertEqual(keys, sorted(keys))
                source_ids = [event.source.community_id for event in truth.events]
                self.assertEqual(source_ids, sorted(set(source_ids)))
                pairs = [(link.source.community_id, link.target.community_id) for link in truth.links]
                self.assertEqual(pairs, sorted(pairs))
                self.assertTrue(all(event.source.feature_month == "2020-12" and event.target_month == "2021-01"
                                    for event in truth.events))

    def test_six_scenario_truth_feeds_sampler_with_exact_active_nodes(self):
        from reddit_sna.benchmarks.dynamic import sample_snapshots

        for scenario, (source, target) in self.expected.items():
            with self.subTest(scenario=scenario):
                users = {"2020-01": self.background.union(*source.values()),
                         "2020-02": self.background.union(*target.values())}
                snapshots = sample_snapshots(
                    build_memberships(scenario, self.reference), expected_reference=self.reference,
                    expected_users_by_month=users, p_in=0, p_out=0,
                )
                for snapshot in snapshots:
                    self.assertEqual(snapshot.nodes, tuple(sorted(users[snapshot.month])))
                    self.assertEqual(snapshot.edges, ())


class TruthFixtureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="reddit-truth-fixture-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    @staticmethod
    def expected_groups(scenario, source_month="2020-01", target_month="2020-02"):
        # Independent fixture expectations; never infer coverage from actual rows.
        original = {f"u{i:03d}" for i in range(1, 13)}
        background = {f"u{i:03d}" for i in range(101, 113)}
        newcomers = {f"u{i:03d}" for i in range(13, 19)} if scenario == "grow" else set()
        return {
            source_month: {"A": original, "K": background},
            target_month: {"C": original | newcomers, "K": background},
        }

    def test_csv_read_independently_matches_exact_members_and_transition_truth(self):
        for scenario in ("stable", "grow"):
            for source_month, target_month in (("2020-01", "2020-02"), ("2020-12", "2021-01")):
                with self.subTest(scenario=scenario, source_month=source_month):
                    reference = f"truth-{scenario}-fixture"
                    expected = self.expected_groups(scenario, source_month, target_month)
                    users = {month: set().union(*groups.values()) for month, groups in expected.items()}
                    rows = build_memberships(scenario, reference, start_month=source_month)
                    path = self.root / f"{scenario}-{source_month}-membership.csv"
                    write_memberships(
                        path, reversed(rows), expected_reference=reference,
                        expected_users_by_month=users,
                    )
                    # Use stdlib CSV rather than the project's inverse adapter.
                    with path.open(encoding="utf-8", newline="") as handle:
                        reader = csv.DictReader(handle)
                        self.assertEqual(reader.fieldnames, ["reference_id", "month", "community_id", "user_id"])
                        records = list(reader)
                    self.assertEqual({row["reference_id"] for row in records}, {reference})
                    self.assertEqual(len(records), 48 if scenario == "stable" else 54)
                    keys = {(row["month"], row["user_id"]) for row in records}
                    self.assertEqual(len(keys), len(records))
                    actual = defaultdict(lambda: defaultdict(set))
                    for row in records:
                        actual[row["month"]][row["community_id"]].add(row["user_id"])
                    self.assertEqual(actual, expected)

                    for month, expected_users in users.items():
                        node_path = self.root / f"{scenario}-{month}-nodes.csv"
                        write_nodes(node_path, month, expected_users)
                        with node_path.open(encoding="utf-8", newline="") as handle:
                            reader = csv.DictReader(handle)
                            self.assertEqual(reader.fieldnames, ["month", "user_id"])
                            node_rows = list(reader)
                        self.assertEqual({row["month"] for row in node_rows}, {month})
                        self.assertEqual([row["user_id"] for row in node_rows], sorted(expected_users))

                    truth = build_transitions(scenario, reference, start_month=source_month)
                    events = {row.source: row for row in truth.events}
                    self.assertEqual(len(events), 2)
                    self.assertEqual(len(truth.events), len(truth.links))
                    self.assertEqual(
                        {row.source.community_id for row in truth.events}, set(actual[source_month]),
                    )
                    for link in truth.links:
                        source_users = actual[link.source.feature_month][link.source.community_id]
                        target_users = actual[link.target.feature_month][link.target.community_id]
                        event = events[link.source]
                        self.assertEqual(event.target_month, link.target.feature_month)
                        if link.source.community_id == "A" and scenario == "grow":
                            self.assertEqual(event.event, Event.GROW)
                            self.assertTrue(source_users < target_users)
                            self.assertEqual(len(target_users - source_users), 6)
                        else:
                            self.assertEqual(event.event, Event.STABLE)
                            self.assertEqual(source_users, target_users)

    def test_corrupted_scenario_csv_is_rejected_without_changing_the_input(self):
        for scenario in ("stable", "grow"):
            reference = f"truth-{scenario}-fixture"
            groups = self.expected_groups(scenario)
            expected_users = {month: set().union(*partition.values()) for month, partition in groups.items()}
            rows = build_memberships(scenario, reference)
            valid = [[row.reference_id, row.month, row.community_id, row.user_id] for row in rows]
            corruptions = {
                "duplicate": (valid + [valid[0]], "duplicate membership"),
                "duplicate_other_group": (valid + [[reference, "2020-01", "K", "u001"]], "duplicate membership"),
                "missing": (valid[1:], "missing expected users"),
                "unexpected": ([[reference, "2020-01", "A", "outside-fixture"]] + valid[1:], "unexpected user"),
                "mixed_reference": ([["other-reference", *valid[0][1:]]] + valid[1:], "reference"),
                "outside_month": ([[reference, "2020-03", "A", "u001"]] + valid[1:], "declared months"),
            }
            for name, (records, message) in corruptions.items():
                with self.subTest(scenario=scenario, corruption=name):
                    path = self.root / f"{scenario}-{name}.csv"
                    with path.open("w", encoding="utf-8", newline="") as handle:
                        writer = csv.writer(handle, lineterminator="\n")
                        writer.writerow(["reference_id", "month", "community_id", "user_id"])
                        writer.writerows(records)
                    original = path.read_bytes()
                    with self.assertRaisesRegex(ValueError, message):
                        read_memberships(
                            path, expected_reference=reference, expected_users_by_month=expected_users,
                        )
                    self.assertEqual(path.read_bytes(), original)

    def test_csv_bytes_and_transition_records_repeat_in_fresh_python_processes(self):
        script = """
import json
from pathlib import Path
import sys
from reddit_sna.benchmarks.io import write_memberships, write_nodes
from reddit_sna.benchmarks.scenarios import build_memberships, build_transitions

output, scenario = Path(sys.argv[1]), sys.argv[2]
reference = "truth-fresh-process"
rows = build_memberships(scenario, reference)
users = {month: {row.user_id for row in rows if row.month == month}
         for month in ("2020-01", "2020-02")}
for month, ids in users.items():
    write_nodes(output / (month + "-nodes.csv"), month, ids)
write_memberships(output / "membership.csv", rows,
                  expected_reference=reference, expected_users_by_month=users)
truth = build_transitions(scenario, reference, observed_months=set(users))
print(json.dumps({
    "events": [[e.source.reference_id, e.source.feature_month,
                e.source.community_id, e.target_month, e.event.value] for e in truth.events],
    "links": [[l.source.reference_id, l.source.feature_month, l.source.community_id,
               l.target.feature_month, l.target.community_id] for l in truth.links],
}))
"""
        for scenario in ("stable", "grow"):
            with self.subTest(scenario=scenario):
                outputs, truths = [], []
                for seed in ("0", "137"):
                    output = self.root / f"{scenario}-hashseed-{seed}"
                    output.mkdir()
                    completed = subprocess.run(
                        [sys.executable, "-c", script, str(output), scenario],
                        env=dict(os.environ, PYTHONHASHSEED=seed), capture_output=True,
                        text=True, encoding="utf-8", timeout=30,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    outputs.append({path.name: path.read_bytes() for path in output.iterdir()})
                    truths.append(json.loads(completed.stdout))
                self.assertEqual(set(outputs[0]), {"membership.csv", "2020-01-nodes.csv", "2020-02-nodes.csv"})
                self.assertEqual(outputs[0], outputs[1])
                self.assertEqual(truths[0], truths[1])
                expected_event = "grow" if scenario == "grow" else "stable"
                self.assertEqual(truths[0]["events"], [
                    ["truth-fresh-process", "2020-01", "A", "2020-02", expected_event],
                    ["truth-fresh-process", "2020-01", "K", "2020-02", "stable"],
                ])
                self.assertEqual(truths[0]["links"], [
                    ["truth-fresh-process", "2020-01", "A", "2020-02", "C"],
                    ["truth-fresh-process", "2020-01", "K", "2020-02", "K"],
                ])
