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
from reddit_sna.pipelines.detection_tracking import detect_synthetic_dataset, export_synthetic_detection
from reddit_sna.pipelines.detection_tracking import _write_detection_json
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
        self.assertEqual(len(result["source_files"]), 6)
        self.assertEqual(result["source_files"]["metadata.json"]["sha256"], sha256(before["metadata.json"]).hexdigest())
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

    def test_export_persists_diagnostics_config_and_portable_month_seed_mapping_without_truth(self):
        original = self.source(detector_seeds=[0])
        source = self.root / "graph only"
        shutil.copytree(original, source, ignore=shutil.ignore_patterns("truth"))
        runtime = ROOT / "configs/benchmark_week1.json"
        before, config_bytes = self.files(source), runtime.read_bytes()
        output = self.root / "detection package"
        metadata = export_synthetic_detection(source, output, benchmark_config=runtime)
        self.assertEqual(json.loads((output / "metadata.json").read_text(encoding="utf-8")), metadata)
        self.assertEqual(self.files(source), before)
        self.assertEqual(runtime.read_bytes(), config_bytes)
        self.assertEqual(metadata["artifact_type"], "synthetic-detection")
        self.assertEqual(metadata["scope"], "detection")
        self.assertEqual(metadata["completed_stages"], ["detection"])
        self.assertEqual(metadata["schema_version"], 1)
        self.assertEqual(metadata["diagnostics_schema_version"], 2)
        self.assertEqual(metadata["membership_schema_version"], 1)
        self.assertEqual(metadata["split"], "development")
        self.assertEqual(metadata["scenario"], "stable")
        self.assertEqual(metadata["generator_seed"], 11)
        self.assertEqual(metadata["truth_reference"], "truth-dev-stable-easy-g11")
        self.assertEqual(metadata["source"]["directory"], str(source.resolve()))
        self.assertEqual(len(metadata["source"]["files"]), 6)
        for name, info in metadata["source"]["files"].items():
            self.assertEqual(info["sha256"], sha256(before[name]).hexdigest())
        detector = metadata["detector"]
        self.assertEqual(detector["seeds"], [0, 1, 2])
        self.assertEqual(detector["canonical_seed"], 0)
        self.assertEqual(detector["gamma"], 1.0)
        self.assertEqual((output / detector["config_file"]).read_bytes(), config_bytes)
        self.assertEqual(detector["config_sha256"], sha256(config_bytes).hexdigest())
        diagnostics = json.loads((output / metadata["diagnostics_file"]).read_text(encoding="utf-8"))
        self.assertEqual(diagnostics["versions"], detector["versions"])
        self.assertEqual(set(detector["versions"]), {"igraph", "leidenalg"})
        self.assertTrue(all(isinstance(v, str) and v for v in detector["versions"].values()))
        self.assertEqual(diagnostics["source_files"], metadata["source"]["files"])
        self.assertEqual(diagnostics["source_dataset"], str(source.resolve()))
        self.assertEqual(diagnostics["detector_config"]["source"], str(runtime.resolve()))
        self.assertEqual(metadata["snapshot_cohort_sha256"], diagnostics["snapshot_cohort_sha256"])
        self.assertEqual(metadata["graph_protocol"], GRAPH_PROTOCOL)
        self.assertEqual(len(metadata["memberships"]), 6)
        self.assertEqual([(m["month"], m["seed"]) for m in metadata["memberships"]],
                         [(m, s) for m in metadata["observed_months"] for s in (0, 1, 2)])
        self.assertEqual(len(set(metadata["detector_references"].values())), 3)
        self.assertEqual(set(metadata["files"]), set(self.files(output)) - {"metadata.json"})
        self.assertEqual(len(metadata["files"]), 8)
        for info in metadata["memberships"]:
            self.assertEqual(info["dataset_id"], metadata["dataset_id"])
            self.assertEqual(info["identity_scope"], metadata["identity_scope"])
            self.assertEqual(info["canonical"], info["seed"] == 0)
            self.assertEqual(info["reference_id"], metadata["detector_references"][str(info["seed"])])
            self.assertEqual(info["sha256"], metadata["files"][info["path"]]["sha256"])
            self.assertEqual(info["graph_file"], f"snapshots/{info['month']}/R.csv")
            self.assertEqual(info["nodes_file"], f"snapshots/{info['month']}/nodes.csv")
            month = next(m for m in diagnostics["months"] if m["month"] == info["month"])
            self.assertEqual(info["graph_sha256"], month["graph_sha256"])
            with (source / info["graph_file"]).open(encoding="utf-8", newline="") as handle:
                endpoints = {row[key] for row in csv.DictReader(handle)
                             for key in ("source_user_id", "target_user_id")}
            with (output / info["path"]).open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, ["reference_id", "month", "community_id", "user_id"])
                rows = list(reader)
            self.assertEqual({r["user_id"] for r in rows}, endpoints)
            self.assertEqual(len(rows), info["assigned_users"])
            self.assertEqual({r["reference_id"] for r in rows}, {info["reference_id"]})
            self.assertEqual({r["month"] for r in rows}, {info["month"]})
            self.assertEqual(info["active_nodes"], info["assigned_users"] + info["isolates"])
        for name in ("detection.json", "metadata.json"):
            self.assertNotIn(b"\r", (output / name).read_bytes())
        # A recipient can resolve every output entry after moving just the package.
        moved = self.root / "recipient copy"
        shutil.copytree(output, moved)
        relocated = json.loads((moved / "metadata.json").read_text(encoding="utf-8"))
        for name, info in relocated["files"].items():
            self.assertFalse(Path(name).is_absolute())
            self.assertNotIn("..", Path(name).parts)
            self.assertEqual(sha256((moved / name).read_bytes()).hexdigest(), info["sha256"])

    def test_export_empty_memberships_keep_reference_and_isolate_mapping(self):
        source = self.source(zero_edges=True)
        output = self.root / "empty-package"
        meta = export_synthetic_detection(source, output)
        diagnostics = json.loads((output / "detection.json").read_text(encoding="utf-8"))
        self.assertEqual(len(meta["memberships"]), 6)
        for info in meta["memberships"]:
            self.assertEqual(info["active_nodes"], 24)
            self.assertEqual(info["assigned_users"], 0)
            self.assertEqual(info["isolates"], 24)
            self.assertEqual(info["status"], "empty_graph_no_partition")
            self.assertEqual(info["reference_id"], meta["detector_references"][str(info["seed"])])
            self.assertEqual((output / info["path"]).read_bytes(), b"reference_id,month,community_id,user_id\n")
        for month in diagnostics["months"]:
            self.assertEqual(month["seed_pair_ARI"], [])
            self.assertTrue(all(run["modularity"] is None and run["rb_objective"] is None
                                for run in month["runs"]))

    def test_export_refuses_existing_or_overlapping_output_before_detection(self):
        source = self.source()
        existing = self.root / "old-package"
        existing.mkdir()
        (existing / "metadata.json").write_bytes(b"preserve old result")
        empty = self.root / "empty-old-package"
        empty.mkdir()
        before_source, before_output = self.files(source), self.files(existing)
        with patch("reddit_sna.pipelines.detection_tracking.detect_synthetic_dataset") as detector:
            for output in (existing, empty):
                with self.subTest(output=output), self.assertRaises(FileExistsError):
                    export_synthetic_detection(source, output)
            for output in (source, source / "new-child", self.root):
                with self.subTest(output=output), self.assertRaisesRegex(ValueError, "overlap"):
                    export_synthetic_detection(source, output)
            with self.assertRaisesRegex(ValueError, "parent"):
                export_synthetic_detection(source, self.root / "missing-parent/result")
            detector.assert_not_called()
        self.assertEqual(self.files(source), before_source)
        self.assertEqual(self.files(existing), before_output)
        self.assertEqual(list(empty.iterdir()), [])

    def test_export_serialization_failure_never_publishes_complete_metadata(self):
        source = self.source()
        before = self.files(source)

        def fail_metadata(path, value):
            if path.name == "metadata.json":
                raise OSError("injected metadata write failure")
            _write_detection_json(path, value)

        output = self.root / "failed-package"
        with patch("reddit_sna.pipelines.detection_tracking._write_detection_json", side_effect=fail_metadata):
            with self.assertRaisesRegex(OSError, "injected metadata"):
                export_synthetic_detection(source, output)
        self.assertFalse(output.exists())
        self.assertEqual(self.files(source), before)
        self.assertFalse(list(self.root.glob("synthetic-detection-export-*")))

    def test_export_rechecks_source_metadata_before_publishing_mapping(self):
        source = self.source()
        metadata = source / "metadata.json"
        original = metadata.read_bytes()

        def mutate_after_detection(path, value):
            _write_detection_json(path, value)
            if path.name == "detection.json":
                metadata.write_bytes(original + b"\n")

        output = self.root / "changed-source-package"
        with patch("reddit_sna.pipelines.detection_tracking._write_detection_json", side_effect=mutate_after_detection):
            with self.assertRaisesRegex(ValueError, "changed before export"):
                export_synthetic_detection(source, output)
        self.assertFalse(output.exists())
