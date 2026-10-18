"""Fresh-process graph export, failure provenance and output isolation."""

from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from reddit_sna.benchmarks.config import load_benchmark_config
from reddit_sna.benchmarks.graphs import export_development_graphs
from reddit_sna.benchmarks.io import export_graph_dataset
from reddit_sna.config import load_config
from tests.support import ProjectCase

BENCHMARK = Path(__file__).resolve().parents[2] / "configs/benchmark_week1.json"


class GraphRunTests(ProjectCase):
    def setup_configs(self):
        config = self.config("detection-tracking")
        self.change(config, "seed = 42", "seed = 11")
        benchmark = self.root / "configs/benchmark.json"
        benchmark.write_bytes(BENCHMARK.read_bytes())
        return config, benchmark

    @staticmethod
    def files(root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def test_cli_exports_six_repeatable_development_datasets_and_preserves_old_run(self):
        config, benchmark = self.setup_configs()
        original_inputs = {p: p.read_bytes() for p in (config, benchmark, self.marker)}
        command = [sys.executable, "-m", "reddit_sna.benchmarks.graphs", "--config", str(config),
                   "--benchmark-config", str(benchmark), "--run-id"]
        runs = []
        for name, hash_seed in (("graph-one", "0"), ("graph-two", "137")):
            result = subprocess.run(command + [name], cwd=self.root,
                                    env={**os.environ, "PYTHONHASHSEED": hash_seed},
                                    capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["scope"], "graph-truth")
            runs.append(Path(json.loads(result.stdout)["run_directory"]))
        first, second = runs
        self.assertEqual(self.files(first / "datasets"), self.files(second / "datasets"))
        manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(manifest["completed_stages"], ["generation", "truth"])
        self.assertEqual(len(manifest["datasets"]), 6)
        self.assertTrue(all(name.startswith("dev-") and name.endswith("-g11") for name in manifest["datasets"]))
        self.assertEqual(set(manifest["files"]), {"datasets/" + name for name in self.files(first / "datasets")})
        self.assertEqual(len(manifest["files"]), 54)
        for name, info in manifest["files"].items():
            self.assertEqual(sha256((first / name).read_bytes()).hexdigest(), info["sha256"])
        before = self.files(first)
        repeated = subprocess.run(command + ["graph-one"], cwd=self.root,
                                  capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(repeated.returncode, 2)
        self.assertIn("already exists", repeated.stderr)
        self.assertEqual(self.files(first), before)
        empty_config = replace(load_config(config), run_id="empty-existing")
        empty_config.run_directory.mkdir()
        with self.assertRaises(ValueError):
            export_development_graphs(empty_config, load_benchmark_config(benchmark))
        self.assertEqual(list(empty_config.run_directory.iterdir()), [])
        for path, content in original_inputs.items():
            self.assertEqual(path.read_bytes(), content)

    def test_failed_run_records_failure_preserves_finished_and_partial_datasets(self):
        config_path, benchmark_path = self.setup_configs()
        config = load_config(config_path)
        benchmark = load_benchmark_config(benchmark_path)

        def fail_grow(destination, **kwargs):
            if kwargs["scenario"] == "grow":
                destination.mkdir()
                (destination / "partial.txt").write_text("preserve", encoding="utf-8")
                raise OSError("simulated graph export failure")
            return export_graph_dataset(destination, **kwargs)

        with patch("reddit_sna.benchmarks.graphs.export_graph_dataset", side_effect=fail_grow):
            with self.assertRaisesRegex(OSError, "simulated"):
                export_development_graphs(config, benchmark)
        run = config.run_directory
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["completed_stages"], [])
        self.assertEqual(manifest["datasets"], ["dev-stable-easy-g11"])
        self.assertIn("simulated", manifest["error"])
        self.assertTrue(manifest["finished_at"])
        self.assertTrue((run / "datasets/dev-stable-easy-g11/metadata.json").is_file())
        self.assertFalse((run / "datasets/dev-grow-easy-g11/metadata.json").exists())
        self.assertEqual((run / "datasets/dev-grow-easy-g11/partial.txt").read_text(), "preserve")
        before = self.files(run)
        with self.assertRaises(ValueError):
            export_development_graphs(config, benchmark)
        self.assertEqual(self.files(run), before)

    def test_invalid_namespace_destination_seed_and_json_are_rejected_before_output(self):
        config_path, benchmark_path = self.setup_configs()
        config = load_config(config_path)
        benchmark = load_benchmark_config(benchmark_path)
        invalid = (replace(config, seed=True), replace(config, seed=101),
                   replace(config, output_root=self.root / "data"),
                   load_config(self.config("prediction")))
        for item in invalid:
            with self.subTest(config=item), self.assertRaises(ValueError):
                export_development_graphs(item, benchmark)
            with self.subTest(config=item, all_seeds=True), self.assertRaises(ValueError):
                export_development_graphs(item, benchmark, all_development_seeds=True)
        with self.assertRaisesRegex(ValueError, "must be bool"):
            export_development_graphs(config, benchmark, all_development_seeds=1)
        benchmark["generator"]["p_out"] = 2
        benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")
        before = self.files(self.root)
        result = subprocess.run(
            [sys.executable, "-m", "reddit_sna.benchmarks.graphs", "--config", str(config_path),
             "--benchmark-config", str(benchmark_path), "--run-id", "invalid-json"],
            cwd=self.root, capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("p_out", result.stderr)
        self.assertFalse((self.root / "artifacts").exists())
        self.assertEqual(self.files(self.root), before)

    def test_all_development_seeds_cli_exports_exactly_the_full_dev_schedule(self):
        config, benchmark = self.setup_configs()
        result = subprocess.run(
            [sys.executable, "-m", "reddit_sna.benchmarks.graphs", "--config", str(config),
             "--benchmark-config", str(benchmark), "--run-id", "all-dev", "--all-development-seeds"],
            cwd=self.root, capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        run = Path(json.loads(result.stdout)["run_directory"])
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        expected = [f"dev-{case}-easy-g{seed}" for case in ("stable", "grow", "shrink", "merge", "split", "dissolve")
                    for seed in (11, 12, 13)]
        self.assertEqual(manifest["datasets"], expected)
        self.assertEqual(manifest["selection"], {"mode": "all-development-seeds", "generator_seeds": [11, 12, 13]})
        self.assertEqual(manifest["completed_stages"], ["generation", "truth"])
        self.assertEqual(len(manifest["files"]), 162)
        reader = Path(__file__).resolve().parents[2] / "scripts/read_graph_dataset.py"
        for dataset_id in expected:
            read = subprocess.run([sys.executable, "-I", str(reader), str(run / "datasets" / dataset_id)],
                                  cwd=self.root, capture_output=True, text=True, encoding="utf-8", timeout=20)
            self.assertEqual(read.returncode, 0, read.stderr)
            summary = json.loads(read.stdout)
            self.assertIs(summary["verified"], True)
            self.assertEqual(summary["dataset_id"], dataset_id)
            self.assertEqual(summary["split"], "development")
        for name, info in manifest["files"].items():
            self.assertEqual(sha256((run / name).read_bytes()).hexdigest(), info["sha256"])

    def test_all_seed_failure_preserves_the_completed_seed_and_failed_manifest(self):
        config_path, benchmark_path = self.setup_configs()
        config = load_config(config_path)
        benchmark = load_benchmark_config(benchmark_path)
        calls = []

        def fail_second_seed(destination, **kwargs):
            calls.append(kwargs["generator_seed"])
            if kwargs["generator_seed"] == 12:
                raise OSError("simulated second seed failure")
            return export_graph_dataset(destination, **kwargs)

        with patch("reddit_sna.benchmarks.graphs.export_graph_dataset", side_effect=fail_second_seed):
            with self.assertRaisesRegex(OSError, "second seed"):
                export_development_graphs(config, benchmark, all_development_seeds=True)
        manifest = json.loads((config.run_directory / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(calls, [11, 12])
        self.assertEqual(manifest["datasets"], ["dev-stable-easy-g11"])
        self.assertEqual(manifest["selection"]["generator_seeds"], [11, 12, 13])
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["completed_stages"], [])
        self.assertTrue((config.run_directory / "datasets/dev-stable-easy-g11/metadata.json").is_file())
