"""Graph CSV and dataset export contracts, independently checked with stdlib."""

from copy import deepcopy
import csv
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reddit_sna.benchmarks.config import load_benchmark_config
from reddit_sna.benchmarks.io import (
    EDGE_COLUMNS, export_graph_dataset, read_edges, read_memberships, read_nodes, write_edges,
)
from reddit_sna.contracts import SnapshotEdge

BENCHMARK = Path(__file__).resolve().parents[2] / "configs/benchmark_week1.json"


class GraphExportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="reddit-graph-export-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.benchmark = load_benchmark_config(BENCHMARK)

    def export(self, name="dataset", **overrides):
        args = dict(benchmark=self.benchmark, scenario="stable", generator_seed=11)
        args.update(overrides)
        return export_graph_dataset(self.root / name, **args)

    @staticmethod
    def files(root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def test_edge_round_trip_sorts_preserves_isolates_and_refuses_overwrite(self):
        path = self.root / "R.csv"
        rows = (SnapshotEdge("2020-01", "a", "c", 2.5), SnapshotEdge("2020-01", "a", "b", 1))
        expected = dict(expected_month="2020-01", expected_users=["a", "b", "c", "isolate"])
        write_edges(path, rows, **expected)
        self.assertEqual(read_edges(path, **expected), tuple(reversed(rows)))
        before = path.read_bytes()
        self.assertNotIn(b"\r", before)
        self.assertFalse(before.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(before.splitlines()[0].decode(), ",".join(EDGE_COLUMNS))
        with self.assertRaises(FileExistsError):
            write_edges(path, [], **expected)
        self.assertEqual(path.read_bytes(), before)
        empty = self.root / "empty.csv"
        write_edges(empty, [], **expected)
        self.assertEqual(read_edges(empty, **expected), ())
        self.assertEqual(empty.read_text(encoding="utf-8"), ",".join(EDGE_COLUMNS) + "\n")

    def test_invalid_edge_records_fail_before_file_creation(self):
        valid = SnapshotEdge("2020-01", "a", "b", 1)
        cases = [([valid, valid], {}), ([SnapshotEdge("2020-01", "b", "a", 1)], {}),
                 ([SnapshotEdge("2020-02", "a", "b", 1)], {}),
                 ([SnapshotEdge("2020-01", "a", "outside", 1)], {}),
                 ([SnapshotEdge("2020-01", "a", "b", True)], {}), ([object()], {}),
                 ([valid], {"expected_users": ["a", "a"]}),
                 ([valid], {"expected_month": "2020-13"}), ([valid], {"expected_users": "ab"})]
        for index, (rows, overrides) in enumerate(cases):
            path = self.root / f"invalid-{index}.csv"
            expected = dict(expected_month="2020-01", expected_users=["a", "b"])
            expected.update(overrides)
            with self.subTest(index=index), self.assertRaises(ValueError):
                write_edges(path, rows, **expected)
            self.assertFalse(path.exists())

    def test_reader_rejects_malformed_or_invalid_edges_without_changing_input(self):
        header = ",".join(EDGE_COLUMNS) + "\n"
        records = ["2020-01,a,a,1\n", "2020-01,a,b,0\n", "2020-01,a,b,-1\n",
                   "2020-01,a,b,nan\n", "2020-01,a,b,inf\n", "2020-01,a,b,True\n",
                   "2020-01,b,a,1\n", "2020-01,a,outside,1\n", "2020-02,a,b,1\n",
                   "2020-01,a,b,1\n2020-01,a,b,1\n", "\n", "2020-01,a,b,1,extra\n",
                   '2020-01,"a,b,1\n']
        contents = [header + row for row in records] + ["wrong,header\n", "\ufeff" + header]
        for index, content in enumerate(contents):
            path = self.root / f"corrupt-{index}.csv"
            path.write_text(content, encoding="utf-8", newline="\n")
            before = path.read_bytes()
            with self.subTest(index=index), self.assertRaises(ValueError):
                read_edges(path, expected_month="2020-01", expected_users=["a", "b"])
            self.assertEqual(path.read_bytes(), before)

    def test_all_six_packages_have_complete_truth_graphs_config_and_hashes(self):
        # Counts are fixed expectations from the planted design, not sampler output.
        expected_counts = {
            "stable": (24, 24, 48, 2, 2), "grow": (24, 30, 54, 2, 2),
            "shrink": (30, 24, 54, 2, 2), "merge": (36, 36, 72, 3, 3),
            "split": (36, 36, 72, 2, 3), "dissolve": (24, 12, 36, 2, 1),
        }
        for scenario, (first, second, members, events, links) in expected_counts.items():
            with self.subTest(scenario=scenario):
                meta = self.export(scenario, scenario=scenario)
                root = self.root / scenario
                self.assertEqual(meta["artifact_type"], "synthetic-graph-truth")
                self.assertEqual(meta["status"], "complete")
                self.assertEqual(meta["dataset_id"], f"dev-{scenario}-easy-g11")
                self.assertEqual(meta["identity_scope"], meta["dataset_id"])
                self.assertEqual(meta["generator"]["seed"], 11)
                self.assertIs(meta["generator"]["seed_used_for_truth"], False)
                self.assertEqual(meta["detector_references"], {})
                self.assertEqual(meta["counts"]["nodes_by_month"], {"2020-01": first, "2020-02": second})
                self.assertEqual([meta["counts"][key] for key in ("memberships", "events", "links")],
                                 [members, events, links])
                self.assertEqual(json.loads((root / "benchmark-config.json").read_text()), self.benchmark)
                files = self.files(root)
                self.assertEqual(len(files), 9)
                self.assertEqual(set(files), set(meta["files"]) | {"metadata.json"})
                for name, info in meta["files"].items():
                    self.assertEqual(info["sha256"], sha256(files[name]).hexdigest())
                    self.assertNotIn(b"\r", files[name])
                users = {}
                for month in meta["observed_months"]:
                    users[month] = read_nodes(root / f"snapshots/{month}/nodes.csv", expected_month=month)
                    # Independent CSV consumer checks endpoint/order/weight constraints.
                    with (root / f"snapshots/{month}/R.csv").open(newline="", encoding="utf-8") as handle:
                        rows = list(csv.DictReader(handle))
                    pairs = [(row["source_user_id"], row["target_user_id"]) for row in rows]
                    self.assertEqual(pairs, sorted(set(pairs)))
                    self.assertTrue(all(a < b and a in users[month] and b in users[month] for a, b in pairs))
                    self.assertTrue(all(row["month"] == month and float(row["weight"]) == 1 for row in rows))
                    self.assertEqual(len(rows), meta["counts"]["edges_by_month"][month])
                    endpoints = {uid for pair in pairs for uid in pair}
                    self.assertEqual(len(set(users[month]) - endpoints), meta["counts"]["isolates_by_month"][month])
                truth = read_memberships(root / "truth/membership.csv",
                                         expected_reference=meta["truth_reference"], expected_users_by_month=users)
                self.assertEqual(len(truth), members)
                for filename, count in (("events", events), ("links", links)):
                    with (root / f"truth/{filename}.csv").open(newline="", encoding="utf-8") as handle:
                        rows = list(csv.DictReader(handle))
                    self.assertEqual(len(rows), count)
                    self.assertTrue(all(row["reference_id"] == meta["truth_reference"] for row in rows))
                if scenario == "stable":
                    self.assertEqual(meta["files"]["snapshots/2020-01/R.csv"]["sha256"],
                                     "58c34c2a7ba1297a7f536b8b5a55556ee5a8666ab9d65839a6a0876ba1476592")
                    self.assertEqual(meta["counts"]["edges_by_month"], {"2020-01": 76, "2020-02": 53})

    def test_all_six_datasets_repeat_bytes_with_same_config_seed(self):
        before = deepcopy(self.benchmark)
        for scenario in self.benchmark["scenarios"]:
            self.export(scenario + "-one", scenario=scenario)
            self.export(scenario + "-two", scenario=scenario)
            self.assertEqual(self.files(self.root / (scenario + "-one")),
                             self.files(self.root / (scenario + "-two")))
        self.assertEqual(self.benchmark, before)

    def test_zero_probabilities_keep_all_nodes_memberships_and_isolates(self):
        self.benchmark["generator"].update(p_in=0, p_out=0)
        meta = self.export(scenario="dissolve")
        self.assertEqual(meta["counts"]["edges_by_month"], {"2020-01": 0, "2020-02": 0})
        self.assertEqual(meta["counts"]["isolates_by_month"], {"2020-01": 24, "2020-02": 12})
        self.assertEqual(meta["counts"]["memberships"], 36)

    def test_invalid_config_selection_creates_no_destination(self):
        invalid = deepcopy(self.benchmark)
        invalid["generator"]["p_in"] = -1
        cases = [dict(generator_seed=value) for value in (True, -1, 2**32, "11", 101)]
        cases += [dict(scenario="unknown"), dict(split="other"), dict(benchmark=invalid)]
        for index, overrides in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.export(f"invalid-{index}", **overrides)
            self.assertFalse((self.root / f"invalid-{index}").exists())

    def test_existing_empty_complete_and_partial_outputs_are_preserved(self):
        self.export("complete")
        (self.root / "empty").mkdir()
        (self.root / "partial").mkdir()
        (self.root / "partial/marker.txt").write_text("keep", encoding="utf-8")
        for name in ("complete", "empty", "partial"):
            before = self.files(self.root / name)
            with self.subTest(name=name), self.assertRaises(FileExistsError):
                self.export(name)
            self.assertEqual(self.files(self.root / name), before)

    def test_failed_write_or_readback_has_no_complete_metadata(self):
        for name, target, error in (("write-failure", "write_edges", OSError("disk failure")),
                                    ("read-failure", "read_edges", ValueError("corrupt CSV"))):
            with patch(f"reddit_sna.benchmarks.io.{target}", side_effect=error):
                with self.subTest(name=name), self.assertRaises(type(error)):
                    self.export(name)
            self.assertTrue((self.root / name).is_dir())
            self.assertFalse((self.root / name / "metadata.json").exists())
