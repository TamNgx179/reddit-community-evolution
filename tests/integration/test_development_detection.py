"""Development-only detection selection, persisted output and failure preservation."""

from dataclasses import replace
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from reddit_sna.benchmarks.config import dataset_schedule, load_benchmark_config
from reddit_sna.benchmarks.graphs import export_development_graphs
from reddit_sna.config import load_config
from reddit_sna.contracts import PipelineName
from reddit_sna.pipelines.detection_tracking import export_synthetic_detection
from scripts.run_development_detection import run_development_detection
from tests.support import ProjectCase

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_development_detection.py"


@unittest.skipUnless(importlib.util.find_spec("igraph") and importlib.util.find_spec("leidenalg"),
                     "install [graph] for development detection integration")
class DevelopmentDetectionTests(ProjectCase):
    def inputs(self):
        benchmark = load_benchmark_config(ROOT / "configs/benchmark_week1.json")
        benchmark["generator"]["seeds"]["development"] = [11]
        benchmark_path = self.root / "configs/benchmark.json"
        benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")
        gen_path = self.config(pipeline="detection-tracking", run_id="graph-source")
        self.change(gen_path, "seed = 42", "seed = 11")
        gen_path = gen_path.rename(gen_path.with_name("graph-source.toml"))
        source = export_development_graphs(load_config(gen_path), benchmark, all_development_seeds=True)
        path = self.config(pipeline="detection-tracking", run_id="detect-development")
        self.change(path, "seed = 42", "seed = 0")
        return source, load_config(path), benchmark_path, benchmark

    @staticmethod
    def hashes(root):
        return {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest()
                for p in sorted(root.rglob("*")) if p.is_file()}

    def test_all_configured_development_datasets_have_complete_detection_only_manifest(self):
        source, config, benchmark_path, benchmark = self.inputs()
        before = self.hashes(source)
        run = run_development_detection(config, source, benchmark_path)
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        expected = [r["dataset_id"] for r in dataset_schedule(benchmark, "development")]
        self.assertEqual(manifest["datasets"], expected)
        self.assertEqual(len(expected), 6)
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(manifest["scope"], "development-detection")
        self.assertEqual(manifest["completed_stages"], ["detection"])
        self.assertEqual(manifest["split"], "development")
        self.assertEqual(manifest["selection"], {"mode": "all-development-seeds", "generator_seeds": [11]})
        self.assertEqual(manifest["detector"], {"seeds": [0, 1, 2], "gamma": 1.0, "canonical_seed": 0})
        self.assertEqual(manifest["expected_counts"], {"datasets": 6, "snapshots": 12, "memberships": 36})
        self.assertEqual(len(manifest["source_files"]), 37)
        self.assertFalse(any("/truth/" in name for name in manifest["source_files"]))
        self.assertEqual((run / "benchmark-config.json").read_bytes(), benchmark_path.read_bytes())
        for dataset_id in expected:
            meta = json.loads((run / "datasets" / dataset_id / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["dataset_id"], dataset_id)
            self.assertEqual(meta["split"], "development")
            self.assertEqual(len(meta["memberships"]), 6)
        self.assertEqual(len(list(run.rglob("membership-seed*.csv"))), 36)
        self.assertEqual(set(manifest["files"]), set(self.hashes(run)) - {"manifest.json"})
        for name, info in manifest["files"].items():
            self.assertEqual(sha256((run / name).read_bytes()).hexdigest(), info["sha256"])
        self.assertEqual(self.hashes(source), before)

    def test_cli_rejects_complete_old_run_and_incomplete_source_without_overwrite(self):
        source, config, benchmark_path, _ = self.inputs()
        args = [sys.executable, str(SCRIPT), "--config", str(config.source), "--benchmark-config", str(benchmark_path),
                "--source-run", str(source), "--run-id", config.run_id]
        first = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(first.stdout)["scope"], "development-detection")
        before = self.hashes(config.run_directory)
        repeated = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(repeated.returncode, 2)
        self.assertIn("already exists", repeated.stderr)
        self.assertEqual(self.hashes(config.run_directory), before)
        manifest_path = source / "manifest.json"
        bad = json.loads(manifest_path.read_text(encoding="utf-8"))
        bad["datasets"].pop()
        manifest_path.write_text(json.dumps(bad), encoding="utf-8")
        source_before = self.hashes(source)
        args[-1] = "incomplete-source"
        rejected = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("full development schedule", rejected.stderr)
        self.assertFalse((config.run_directory.parent / "incomplete-source").exists())
        self.assertEqual(self.hashes(source), source_before)

    def test_failed_dataset_keeps_prior_package_partial_output_and_failed_manifest(self):
        source, config, benchmark_path, benchmark = self.inputs()
        before_source = self.hashes(source)
        expected = [r["dataset_id"] for r in dataset_schedule(benchmark, "development")]
        count = 0

        def fail_second(source, output, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                output.mkdir()
                (output / "partial-marker.txt").write_bytes(b"preserve incomplete dataset")
                raise OSError("injected second-dataset failure")
            return export_synthetic_detection(source, output, **kwargs)

        with patch("scripts.run_development_detection.export_synthetic_detection", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "injected second-dataset"):
                run_development_detection(config, source, benchmark_path)
        run = config.run_directory
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["datasets"], expected[:1])
        self.assertEqual(manifest["current_dataset"], expected[1])
        self.assertEqual(manifest["completed_stages"], [])
        self.assertTrue((run / "datasets" / expected[0] / "metadata.json").is_file())
        self.assertEqual((run / "datasets" / expected[1] / "partial-marker.txt").read_bytes(), b"preserve incomplete dataset")
        self.assertFalse((run / "datasets" / expected[2]).exists())
        before_failed = self.hashes(run)
        with self.assertRaises(ValueError):
            run_development_detection(config, source, benchmark_path)
        self.assertEqual(self.hashes(run), before_failed)
        self.assertEqual(self.hashes(source), before_source)

    def test_bad_seed_namespace_overlap_or_input_hash_fails_before_output(self):
        source, config, benchmark_path, _ = self.inputs()
        invalid = (replace(config, seed=42), replace(config, pipeline=PipelineName.PREDICTION),
                   replace(config, input_kind="reddit"), replace(config, output_root=source))
        with patch("scripts.run_development_detection.export_synthetic_detection") as backend:
            for bad in invalid:
                with self.subTest(config=bad), self.assertRaises(ValueError):
                    run_development_detection(bad, source, benchmark_path)
            graph = source / "datasets/dev-stable-easy-g11/snapshots/2020-01/R.csv"
            with graph.open("ab") as handle:
                handle.write(b"\n")
            changed_source = self.hashes(source)
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                run_development_detection(config, source, benchmark_path)
            backend.assert_not_called()
        self.assertFalse(config.run_directory.exists())
        self.assertEqual(self.hashes(source), changed_source)
