"""Protocol-to-report composition, development boundary and partial-run behavior."""

import csv
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from reddit_sna.config import ConfigError, load_config
from reddit_sna.contracts import PipelineName
from reddit_sna.pipelines.detection_tracking import run_synthetic_benchmark
from tests.support import ProjectCase

ROOT = Path(__file__).resolve().parents[2]


class BenchmarkFixture(ProjectCase):
    def setup_config(self):
        path = self.config("detection-tracking")
        self.change(path, "seed = 42", "seed = 0")
        for name in ("benchmark_week1.json", "benchmark_week1_protocol.json"):
            (self.root / "configs" / name).write_bytes((ROOT / "configs" / name).read_bytes())
        return load_config(path), self.root / "configs/benchmark_week1_protocol.json"

    @staticmethod
    def files(path):
        return {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob("*") if p.is_file()}

    @staticmethod
    def rows(path):
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))


class SyntheticBenchmarkPreflightTests(BenchmarkFixture):
    def test_namespace_seed_input_and_output_are_validated_before_any_stage(self):
        config, protocol = self.setup_config()
        invalid = [replace(config, pipeline=PipelineName.PREDICTION), replace(config, input_kind="reddit"),
                   replace(config, input_path=self.marker.parent), replace(config, seed=11), replace(config, seed=False),
                   replace(config, output_root=self.root / "data/raw"), replace(config, run_id="../escape")]
        with patch("reddit_sna.pipelines.detection_tracking.dependencies") as backend:
            for bad in invalid:
                with self.subTest(config=bad), self.assertRaises(ConfigError):
                    run_synthetic_benchmark(bad, protocol=protocol)
            backend.assert_not_called()
        self.assertFalse((self.root / "artifacts").exists())

    def test_empty_duplicate_unknown_or_evaluation_selection_is_rejected_before_outputs(self):
        config, protocol = self.setup_config()
        for ids in ([], ["dev-stable-easy-g11"] * 2, ["eval-stable-easy-g101"], ["unknown"],
                    "dev-stable-easy-g11", [None], 1):
            with self.subTest(ids=ids), self.assertRaises(ConfigError):
                run_synthetic_benchmark(config, protocol=protocol, dataset_ids=ids)
        self.assertFalse((self.root / "artifacts").exists())

    def test_bad_protocol_or_missing_backend_does_not_reserve_a_run(self):
        config, protocol = self.setup_config()
        original = protocol.read_bytes()
        protocol.write_bytes(original + b" ")
        # Protocol whitespace itself is allowed; the bound recipe must still match.
        recipe = self.root / "configs/benchmark_week1.json"
        recipe.write_bytes(recipe.read_bytes() + b"\n")
        with self.assertRaisesRegex(ConfigError, "SHA-256"):
            run_synthetic_benchmark(config, protocol=protocol)
        recipe.write_bytes((ROOT / "configs/benchmark_week1.json").read_bytes())
        protocol.write_bytes(original)
        with patch("reddit_sna.pipelines.detection_tracking.dependencies", side_effect=ValueError("graph backend missing")), self.assertRaisesRegex(ValueError, "graph backend"):
            run_synthetic_benchmark(config, protocol=protocol)
        with patch("reddit_sna.pipelines.detection_tracking.dependencies"), patch("importlib.import_module", side_effect=ModuleNotFoundError("sklearn missing", name="sklearn")), self.assertRaisesRegex(ImportError, r"graph,evaluation"):
            run_synthetic_benchmark(config, protocol=protocol)
        self.assertFalse((self.root / "artifacts").exists())


@unittest.skipUnless(all(importlib.util.find_spec(name) for name in ("igraph", "leidenalg", "sklearn")), "install [graph,evaluation] for benchmark integration")
class SyntheticBenchmarkRunTests(BenchmarkFixture):
    def test_one_dataset_runs_all_stages_and_repeat_preserves_completed_output(self):
        config, protocol = self.setup_config()
        before = {p: p.read_bytes() for p in (config.source, protocol, self.marker, self.root / "configs/benchmark_week1.json")}
        output = run_synthetic_benchmark(config, protocol=protocol, dataset_ids=["dev-stable-easy-g11"])
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertEqual((manifest["status"], manifest["scope"], manifest["tracking_status"]),
                         ("complete", "development-detection-evaluation", "not_implemented"))
        self.assertEqual(manifest["completed_stages"], ["generation", "truth", "detection", "evaluation"])
        self.assertEqual(manifest["actual_counts"], {"datasets": 1, "snapshots": 2, "snapshot_detector_runs": 6})
        self.assertEqual(manifest["actual_counts"], manifest["expected_counts"])
        self.assertFalse(manifest["freeze_record_created"])
        self.assertIsNone(manifest["current_stage"])
        self.assertFalse((output / "manifest.pending.json").exists())
        self.assertEqual(len(self.files(output)), 27)
        rows = self.rows(output / "evaluation/detection_metrics.csv")
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(r["ami_status"] == "ok" and float(r["ami"]) == 1 and float(r["coverage"]) == 1 for r in rows))
        saved = self.files(output)
        with self.assertRaises(ConfigError):
            run_synthetic_benchmark(config, protocol=protocol, dataset_ids=["dev-stable-easy-g11"])
        self.assertEqual(self.files(output), saved)
        self.assertTrue(all(p.read_bytes() == value for p, value in before.items()))

    def test_default_runs_18_development_datasets_with_heldout_absent_and_nulls_retained(self):
        config, protocol = self.setup_config()
        output = run_synthetic_benchmark(config, protocol=protocol)
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertEqual(manifest["selection"]["mode"], "full-development")
        self.assertEqual(manifest["actual_counts"], {"datasets": 18, "snapshots": 36, "snapshot_detector_runs": 108})
        self.assertEqual(len(list((output / "inputs/source").iterdir())), 18)
        self.assertTrue(all(name.startswith("dev-") for name in manifest["selection"]["dataset_ids"]))
        rows = self.rows(output / "evaluation/detection_metrics.csv")
        self.assertEqual(len(rows), 108)
        self.assertEqual(sum(r["ami_status"] == "ok" for r in rows), 99)
        missing = [r for r in rows if r["ami_status"] != "ok"]
        self.assertEqual(len(missing), 9)
        self.assertTrue(all(r["ami"] == "" and r["ami_reason"] == "truth_constant" for r in missing))

    def test_cli_from_outside_repo_replays_in_protocol_order_without_overwriting(self):
        config, protocol = self.setup_config()
        base = [sys.executable, "-m", "reddit_sna.pipelines.detection_tracking", "--config", str(config.source), "--protocol", str(protocol)]
        outputs = []
        for run_id, ids in (("first", ["dev-stable-easy-g11", "dev-grow-easy-g11"]),
                            ("second", ["dev-grow-easy-g11", "dev-stable-easy-g11"])):
            command = base + ["--run-id", run_id]
            for dataset in ids:
                command += ["--dataset-id", dataset]
            result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["scope"], "development-detection-evaluation")
            self.assertEqual(data["tracking_status"], "not_implemented")
            outputs.append(Path(data["run_directory"]))
        first, second = outputs
        for name, value in self.files(first).items():
            if name.endswith(".csv") or name == "evaluation/ami-policy.json":
                self.assertEqual(value, (second / name).read_bytes(), name)
        before = self.files(second)
        repeated = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=30)
        self.assertEqual(repeated.returncode, 2)
        self.assertEqual(self.files(second), before)

    def test_detection_failure_keeps_generated_data_and_failed_stage(self):
        config, protocol = self.setup_config()
        with patch("reddit_sna.pipelines.detection_tracking.export_synthetic_detection", side_effect=ValueError("detector failure")), self.assertRaisesRegex(ValueError, "detector failure"):
            run_synthetic_benchmark(config, protocol=protocol, dataset_ids=["dev-stable-easy-g11"])
        manifest = json.loads((config.run_directory / "manifest.json").read_text())
        self.assertEqual((manifest["status"], manifest["current_stage"], manifest["current_dataset"]),
                         ("failed", "detection", "dev-stable-easy-g11"))
        self.assertEqual(manifest["completed_stages"], ["generation", "truth"])
        self.assertTrue((config.run_directory / "inputs/source/dev-stable-easy-g11/metadata.json").is_file())
        self.assertFalse((config.run_directory / "evaluation").exists())

    def test_evaluator_failure_keeps_detection_without_reporting_complete(self):
        config, protocol = self.setup_config()
        with patch("reddit_sna.evaluation.detection.export_detection_evaluation", side_effect=OSError("report failure")), self.assertRaisesRegex(OSError, "report failure"):
            run_synthetic_benchmark(config, protocol=protocol, dataset_ids=["dev-stable-easy-g11"])
        manifest = json.loads((config.run_directory / "manifest.json").read_text())
        self.assertEqual((manifest["status"], manifest["current_stage"]), ("failed", "evaluation"))
        self.assertEqual(manifest["completed_stages"], ["generation", "truth", "detection"])
        self.assertTrue((config.run_directory / "inputs/detected/dev-stable-easy-g11/metadata.json").is_file())

    def test_original_config_change_uses_archived_inputs_but_marks_run_failed(self):
        from reddit_sna.benchmarks.io import export_graph_dataset
        config, protocol = self.setup_config()
        def changing_generator(*args, **kwargs):
            result = export_graph_dataset(*args, **kwargs)
            protocol.write_bytes(protocol.read_bytes() + b"\n")
            return result
        with patch("reddit_sna.pipelines.detection_tracking.export_graph_dataset", side_effect=changing_generator), self.assertRaisesRegex(ValueError, "configuration changed"):
            run_synthetic_benchmark(config, protocol=protocol, dataset_ids=["dev-stable-easy-g11"])
        manifest = json.loads((config.run_directory / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["current_stage"], "evaluation")
        self.assertTrue((config.run_directory / "evaluation/metadata.json").is_file())
