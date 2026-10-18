"""Initial graph-only synthetic adapter: real Leiden, endpoint coverage and safe output."""

import csv
import importlib.util
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from reddit_sna.benchmarks.config import GRAPH_PROTOCOL, load_benchmark_config
from reddit_sna.benchmarks.io import export_graph_dataset, read_edges, read_memberships, read_nodes
from reddit_sna.pipelines.detection_tracking import detect_synthetic_dataset
from tests.support import ProjectCase

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(importlib.util.find_spec("leidenalg") and importlib.util.find_spec("igraph"),
                     "install [graph] for synthetic Leiden integration")
class SyntheticDetectionTests(ProjectCase):
    def source(self, name="source", *, zero_edges=False):
        benchmark = load_benchmark_config(ROOT / "configs/benchmark_week1.json")
        if zero_edges:
            benchmark["generator"].update(p_in=0, p_out=0)
        source = self.root / name
        export_graph_dataset(source, benchmark=benchmark, scenario="stable", generator_seed=11)
        return source

    @staticmethod
    def files(root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def test_seed_zero_detects_graph_only_without_reading_truth_and_writes_canonical_csv(self):
        original = self.source()
        source = self.root / "graph-only"
        shutil.copytree(original, source, ignore=shutil.ignore_patterns("truth"))
        self.assertFalse((source / "truth").exists())
        before = self.files(source)
        output = self.root / "memberships"
        result = detect_synthetic_dataset(source, output)
        self.assertEqual(self.files(source), before)
        self.assertEqual(result["dataset_id"], "dev-stable-easy-g11")
        self.assertEqual(result["identity_scope"], "dev-stable-easy-g11")
        self.assertEqual(result["graph_protocol"], GRAPH_PROTOCOL)
        self.assertEqual(result["canonical_seed"], 0)
        self.assertEqual(result["gamma"], 1.0)
        self.assertEqual(result["membership_schema_version"], 1)
        self.assertEqual(set(result["versions"]), {"igraph", "leidenalg"})
        self.assertEqual(len(result["source_files"]), 5)
        self.assertFalse(any(name.startswith("truth/") for name in result["source_files"]))
        references = set()
        for info in result["months"]:
            month = info["month"]
            self.assertEqual([run["seed"] for run in info["runs"]], [0])
            self.assertEqual(info["seed_pair_ARI"], [])
            run = info["runs"][0]
            nodes = read_nodes(source / f"snapshots/{month}/nodes.csv", expected_month=month)
            edges = read_edges(source / f"snapshots/{month}/R.csv", expected_month=month, expected_users=nodes)
            endpoints = {u for edge in edges for u in (edge.source_user_id, edge.target_user_id)}
            reference = run["reference_id"]
            references.add(reference)
            self.assertTrue(reference.startswith("dev-stable-easy-g11:" + GRAPH_PROTOCOL + ":"))
            self.assertNotEqual(reference, "truth-dev-stable-easy-g11")
            path = output / month / "membership-seed0.csv"
            records = read_memberships(path, expected_reference=reference, expected_users_by_month={month: endpoints})
            self.assertEqual({r.user_id for r in records}, endpoints)
            self.assertEqual(run["assigned_users"], 24)
            self.assertEqual(sum(run["sizes"]), 24)
            self.assertEqual(run["status"], "complete")
            data = path.read_bytes()
            self.assertNotIn(b"\r", data)
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            keys = [(r["month"], r["community_id"], r["user_id"]) for r in rows]
            self.assertEqual(keys, sorted(keys))
        self.assertEqual(len(references), 1)

    def test_empty_graph_keeps_active_isolates_and_no_fabricated_partition(self):
        source = self.source(zero_edges=True)
        result = detect_synthetic_dataset(source, self.root / "empty-memberships")
        for info in result["months"]:
            month = info["month"]
            self.assertEqual(result["active_nodes_by_month"][month], 24)
            self.assertEqual(result["isolates_by_month"][month], 24)
            run = info["runs"][0]
            self.assertEqual(run["assigned_users"], 0)
            self.assertEqual(run["status"], "empty_graph_no_partition")
            self.assertIsNone(run["modularity"])
            self.assertIsNone(run["rb_objective"])
            self.assertEqual(run["communities"], 0)
            self.assertEqual((self.root / f"empty-memberships/{month}/membership-seed0.csv").read_text(encoding="utf-8"),
                             "reference_id,month,community_id,user_id\n")

    def test_changed_graph_or_scope_fails_before_detector_and_creates_no_output(self):
        source = self.source()
        path = source / "snapshots/2020-01/R.csv"
        original = path.read_bytes()
        path.write_bytes(original + original.splitlines(keepends=True)[1])
        with patch("reddit_sna.pipelines.detection_tracking.detect_snapshots") as detector:
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                detect_synthetic_dataset(source, self.root / "bad-graph")
            detector.assert_not_called()
        self.assertFalse((self.root / "bad-graph").exists())
        path.write_bytes(original)
        meta_path = source / "metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["identity_scope"] = "wrong"
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "identity scope"):
            detect_synthetic_dataset(source, self.root / "bad-scope")
        self.assertFalse((self.root / "bad-scope").exists())

    def test_existing_output_and_source_overlap_are_preserved(self):
        source = self.source()
        output = self.root / "existing"
        output.mkdir()
        (output / "marker.txt").write_text("keep", encoding="utf-8")
        before_source, before_output = self.files(source), self.files(output)
        with self.assertRaises(FileExistsError):
            detect_synthetic_dataset(source, output)
        for invalid in (source, source / "new-child", self.root):
            with self.subTest(output=invalid), self.assertRaisesRegex(ValueError, "overlap"):
                detect_synthetic_dataset(source, invalid)
        self.assertEqual(self.files(source), before_source)
        self.assertEqual(self.files(output), before_output)
