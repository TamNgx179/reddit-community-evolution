"""Configured synthetic Leiden: exact seed schedule, endpoint coverage and safe output."""

from copy import deepcopy
import csv
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from reddit_sna.benchmarks.config import GRAPH_PROTOCOL, load_benchmark_config
from reddit_sna.benchmarks.io import export_graph_dataset, read_edges, read_memberships, read_nodes
from reddit_sna.detection.leiden import detect_snapshots as leiden_backend
from reddit_sna.pipelines.detection_tracking import detect_synthetic_dataset
from tests.support import ProjectCase

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(importlib.util.find_spec("leidenalg") and importlib.util.find_spec("igraph"),
                     "install [graph] for synthetic Leiden integration")
class SyntheticDetectionTests(ProjectCase):
    def source(self, name="source", *, zero_edges=False, detector_seeds=None):
        benchmark = load_benchmark_config(ROOT / "configs/benchmark_week1.json")
        if zero_edges:
            benchmark["generator"].update(p_in=0, p_out=0)
        if detector_seeds is not None:
            benchmark["detector"]["seeds"] = detector_seeds
        source = self.root / name
        export_graph_dataset(source, benchmark=benchmark, scenario="stable", generator_seed=11)
        return source

    @staticmethod
    def files(root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def test_configured_seeds_detect_graph_only_without_truth_and_write_canonical_csv(self):
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
        self.assertEqual(result["detector_seeds"], [0, 1, 2])
        self.assertEqual(result["membership_schema_version"], 1)
        self.assertEqual(set(result["versions"]), {"igraph", "leidenalg"})
        self.assertEqual(len(result["source_files"]), 5)
        self.assertFalse(any(name.startswith("truth/") for name in result["source_files"]))
        references = {seed: set() for seed in (0, 1, 2)}
        for info in result["months"]:
            month = info["month"]
            self.assertEqual([run["seed"] for run in info["runs"]], [0, 1, 2])
            self.assertEqual(len(info["seed_pair_ARI"]), 3)
            nodes = read_nodes(source / f"snapshots/{month}/nodes.csv", expected_month=month)
            edges = read_edges(source / f"snapshots/{month}/R.csv", expected_month=month, expected_users=nodes)
            endpoints = {u for edge in edges for u in (edge.source_user_id, edge.target_user_id)}
            for run in info["runs"]:
                seed, reference = run["seed"], run["reference_id"]
                references[seed].add(reference)
                self.assertTrue(reference.startswith("dev-stable-easy-g11:" + GRAPH_PROTOCOL + ":"))
                self.assertTrue(reference.endswith(f"-gamma1-seed{seed}"))
                self.assertNotEqual(reference, "truth-dev-stable-easy-g11")
                path = output / month / f"membership-seed{seed}.csv"
                records = read_memberships(path, expected_reference=reference, expected_users_by_month={month: endpoints})
                self.assertEqual({r.user_id for r in records}, endpoints)
                self.assertEqual(run["assigned_users"], 24)
                self.assertEqual(sum(run["sizes"]), 24)
                self.assertEqual(run["status"], "complete")
                self.assertNotIn(b"\r", path.read_bytes())
                with path.open(encoding="utf-8", newline="") as handle:
                    rows = list(csv.DictReader(handle))
                keys = [(r["month"], r["community_id"], r["user_id"]) for r in rows]
                self.assertEqual(keys, sorted(keys))
        self.assertTrue(all(len(refs) == 1 for refs in references.values()))
        self.assertEqual(len(set().union(*references.values())), 3)

    def test_empty_graph_keeps_active_isolates_and_no_fabricated_partition(self):
        source = self.source(zero_edges=True)
        result = detect_synthetic_dataset(source, self.root / "empty-memberships")
        for info in result["months"]:
            month = info["month"]
            self.assertEqual(result["active_nodes_by_month"][month], 24)
            self.assertEqual(result["isolates_by_month"][month], 24)
            self.assertEqual(info["seed_pair_ARI"], [])
            self.assertEqual([run["seed"] for run in info["runs"]], [0, 1, 2])
            for run in info["runs"]:
                seed = run["seed"]
                self.assertEqual(run["assigned_users"], 0)
                self.assertEqual(run["status"], "empty_graph_no_partition")
                self.assertIsNone(run["modularity"])
                self.assertIsNone(run["rb_objective"])
                self.assertEqual(run["communities"], 0)
                self.assertEqual((self.root / f"empty-memberships/{month}/membership-seed{seed}.csv").read_text(encoding="utf-8"),
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

    def test_explicit_runtime_config_overrides_archived_detector_schedule_read_only(self):
        source = self.source(detector_seeds=[0])
        runtime = self.root / "configs/runtime.json"
        runtime.write_bytes((ROOT / "configs/benchmark_week1.json").read_bytes())
        before_source, before_config = self.files(source), runtime.read_bytes()
        result = detect_synthetic_dataset(source, self.root / "configured", benchmark_config=runtime)
        self.assertEqual(result["detector_seeds"], [0, 1, 2])
        self.assertEqual(result["canonical_seed"], 0)
        self.assertEqual(result["detector_config"]["source"], str(runtime.resolve()))
        self.assertEqual(result["detector_config"]["sha256"], sha256(before_config).hexdigest())
        self.assertEqual(self.files(source), before_source)
        self.assertEqual(runtime.read_bytes(), before_config)
        self.assertEqual(len(list((self.root / "configured").rglob("membership-seed*.csv"))), 6)

    def test_invalid_runtime_schedule_or_graph_recipe_fails_before_output(self):
        source = self.source()
        original = load_benchmark_config(ROOT / "configs/benchmark_week1.json")
        changes = [
            {"seeds": [0]}, {"seeds": [0, 2, 1]}, {"seeds": [1, 0, 2], "canonical_seed": 1},
            {"seeds": [0, 1, 1]}, {"seeds": [True, 1, 2]}, {"canonical_seed": 1},
            {"gamma": 0}, {"gamma": 2},
        ]
        runtime = self.root / "configs/runtime.json"
        with patch("reddit_sna.pipelines.detection_tracking.detect_snapshots") as detector:
            for index, change in enumerate(changes):
                config = deepcopy(original)
                config["detector"].update(change)
                runtime.write_text(json.dumps(config), encoding="utf-8")
                before = runtime.read_bytes()
                output = self.root / f"invalid-{index}"
                with self.subTest(change=change), self.assertRaises(ValueError):
                    detect_synthetic_dataset(source, output, benchmark_config=runtime)
                self.assertFalse(output.exists())
                self.assertEqual(runtime.read_bytes(), before)
            config = deepcopy(original)
            config["generator"]["p_in"] = 0.8
            runtime.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "graph recipe"):
                detect_synthetic_dataset(source, self.root / "wrong-recipe", benchmark_config=runtime)
            self.assertFalse((self.root / "wrong-recipe").exists())
            detector.assert_not_called()

    def test_canonical_stays_zero_even_when_another_seed_has_higher_quality(self):
        source = self.source()

        def higher_seed_two(*args, **kwargs):
            result = leiden_backend(*args, **kwargs)
            for info in result["months"]:
                for run in info["runs"]:
                    run["modularity"] = (0.1, 0.2, 0.9)[run["seed"]]
                    run["rb_objective"] = run["seed"] + 1
            return result

        with patch("reddit_sna.pipelines.detection_tracking.detect_snapshots", side_effect=higher_seed_two):
            result = detect_synthetic_dataset(source, self.root / "fixed-canonical")
        self.assertEqual(result["canonical_seed"], 0)
        for info in result["months"]:
            self.assertEqual(max(info["runs"], key=lambda run: run["modularity"])["seed"], 2)
            self.assertEqual([run["seed"] for run in info["runs"]], [0, 1, 2])
            self.assertTrue(info["runs"][0]["reference_id"].endswith("-seed0"))

    def test_mixed_seed_references_or_reordered_runs_fail_before_publication(self):
        source = self.source()
        for kind in ("reference", "order"):
            def wrong_result(*args, **kwargs):
                result = leiden_backend(*args, **kwargs)
                runs = result["months"][1]["runs"]
                if kind == "reference":
                    runs[1]["reference_id"] = runs[0]["reference_id"]
                else:
                    runs.reverse()
                return result

            output = self.root / ("mixed-" + kind)
            with patch("reddit_sna.pipelines.detection_tracking.detect_snapshots", side_effect=wrong_result):
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    detect_synthetic_dataset(source, output)
            self.assertFalse(output.exists())
