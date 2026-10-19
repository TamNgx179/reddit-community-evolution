"""Protocol-to-report composition, development boundary and partial-run behavior."""

import csv
from dataclasses import replace
from hashlib import sha256
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
    def test_schema_two_records_exact_hashes_source_environment_and_timing_scopes(self):
        config, protocol = self.setup_config()
        output = run_synthetic_benchmark(config, protocol=protocol, dataset_ids=["dev-stable-easy-g11"])
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertEqual(manifest["schema_version"], 2)
        files = self.files(output)
        self.assertEqual(set(manifest["files"]), set(files) - {"manifest.json"})
        for name, info in manifest["files"].items():
            self.assertEqual(info, {"sha256": sha256(files[name]).hexdigest(), "bytes": len(files[name])}, name)
        for info in [*manifest["config_inputs"].values(), manifest["resolved_config"]]:
            self.assertEqual(info["sha256"], sha256(files[info["archive"]]).hexdigest())
        self.assertEqual(json.loads(files[manifest["resolved_config"]["archive"]]), config.to_dict())
        self.assertNotEqual(Path(manifest["source"]["package_directory"]), self.root / "src/reddit_sna")
        self.assertIn("reddit_sna/artifacts.py", manifest["source"]["files"])
        for name, digest in manifest["source"]["files"].items():
            self.assertEqual(sha256(files[manifest["source"]["archive_root"] + "/" + name]).hexdigest(), digest)
        self.assertEqual(json.loads(files["provenance/environment.json"]), manifest["environment"])
        self.assertEqual(json.loads(files["provenance/source.json"]), manifest["source"])
        self.assertEqual(manifest["environment"]["python_executable"], sys.executable)
        self.assertTrue(all(manifest["environment"]["packages"].values()))
        self.assertEqual(manifest["integrity"], {"status": "verified", "output_files": len(manifest["files"]), "source_unchanged": True})
        self.assertEqual(manifest["progress_counts"], {"generated_datasets": 1, "detected_datasets": 1, "evaluated_datasets": 1})
        durations = []
        for record in manifest["stages"].values():
            self.assertEqual(record["status"], "complete")
            self.assertIsNotNone(record["started_at"])
            self.assertIsNotNone(record["finished_at"])
            self.assertGreaterEqual(record["wall_seconds"], 0)
            durations.append(record["wall_seconds"])
        timing = manifest["timing"]
        self.assertGreaterEqual(timing["run_wall_seconds"], sum(durations) + timing["verification_wall_seconds"])
        self.assertGreaterEqual(manifest["preflight_wall_seconds"], 0)
        self.assertIsNone(timing["peak_memory_bytes"])
        record = manifest["dataset_records"]["dev-stable-easy-g11"]
        for stage in ("generation", "detection"):
            self.assertEqual(record[stage]["status"], "complete")
            self.assertGreaterEqual(record[stage]["wall_seconds"], 0)
        self.assertEqual(record["evaluation"]["status"], "complete")
        self.assertIsNone(record["evaluation"]["wall_seconds"])
        self.assertIn("batch", record["evaluation"]["scope"])

    def test_generation_failure_inventories_partial_files_and_preserves_pending_stages(self):
        config, protocol = self.setup_config()
        def failing_generator(output, **kwargs):
            output.mkdir()
            (output / "partial.txt").write_bytes(b"partial graph")
            raise OSError("generator disk failure")
        with patch("reddit_sna.pipelines.detection_tracking.export_graph_dataset", side_effect=failing_generator), self.assertRaisesRegex(OSError, "generator disk failure"):
            run_synthetic_benchmark(config, protocol=protocol, dataset_ids=["dev-stable-easy-g11"])
        manifest = json.loads((config.run_directory / "manifest.json").read_text())
        self.assertEqual((manifest["status"], manifest["current_stage"]), ("failed", "generation"))
        self.assertEqual(manifest["stages"]["generation"]["status"], "failed")
        self.assertGreaterEqual(manifest["stages"]["generation"]["wall_seconds"], 0)
        self.assertEqual(manifest["files"]["inputs/source/dev-stable-easy-g11/partial.txt"],
                         {"sha256": sha256(b"partial graph").hexdigest(), "bytes": 13})
        record = manifest["dataset_records"]["dev-stable-easy-g11"]
        self.assertEqual(record["generation"]["status"], "failed")
        for stage in ("detection", "evaluation"):
            self.assertEqual(record[stage], {"status": "pending", "wall_seconds": None})
            self.assertEqual(manifest["stages"][stage]["status"], "pending")
        self.assertEqual(manifest["progress_counts"], {"generated_datasets": 0, "detected_datasets": 0, "evaluated_datasets": 0})

    def test_second_detector_failure_keeps_first_complete_and_partial_second_dataset(self):
        from reddit_sna.pipelines.detection_tracking import export_synthetic_detection
        config, protocol = self.setup_config()
        def second_fails(source, output, **kwargs):
            if source.name == "dev-stable-easy-g11":
                return export_synthetic_detection(source, output, **kwargs)
            output.mkdir()
            (output / "partial.txt").write_bytes(b"partial detection")
            raise ValueError("second detector failed")
        with patch("reddit_sna.pipelines.detection_tracking.export_synthetic_detection", side_effect=second_fails), self.assertRaisesRegex(ValueError, "second detector failed"):
            run_synthetic_benchmark(config, protocol=protocol, dataset_ids=["dev-stable-easy-g11", "dev-grow-easy-g11"])
        manifest = json.loads((config.run_directory / "manifest.json").read_text())
        self.assertEqual(manifest["current_dataset"], "dev-grow-easy-g11")
        self.assertEqual(manifest["progress_counts"], {"generated_datasets": 2, "detected_datasets": 1, "evaluated_datasets": 0})
        self.assertEqual(manifest["dataset_records"]["dev-stable-easy-g11"]["detection"]["status"], "complete")
        self.assertEqual(manifest["dataset_records"]["dev-grow-easy-g11"]["detection"]["status"], "failed")
        self.assertIn("inputs/detected/dev-grow-easy-g11/partial.txt", manifest["files"])
        self.assertIn("inputs/detected/dev-stable-easy-g11/metadata.json", manifest["files"])
        self.assertFalse((config.run_directory / "evaluation").exists())

    def test_sealed_output_change_fails_with_expected_and_actual_hashes(self):
        from reddit_sna.pipelines.detection_tracking import export_synthetic_detection
        config, protocol = self.setup_config()
        name = "config/resolved-run-config.json"
        expected = {}
        def changing_detector(*args, **kwargs):
            result = export_synthetic_detection(*args, **kwargs)
            expected.update(sha256=sha256((config.run_directory / name).read_bytes()).hexdigest(),
                            bytes=(config.run_directory / name).stat().st_size)
            (config.run_directory / name).write_bytes(b"changed output")
            return result
        with patch("reddit_sna.pipelines.detection_tracking.export_synthetic_detection", side_effect=changing_detector), self.assertRaisesRegex(ValueError, "sealed run outputs changed"):
            run_synthetic_benchmark(config, protocol=protocol, dataset_ids=["dev-stable-easy-g11"])
        manifest = json.loads((config.run_directory / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["integrity"]["changed_sealed_outputs"], [name])
        self.assertEqual(manifest["integrity"]["output_changes"][name], {"expected": expected,
            "actual": {"sha256": sha256(b"changed output").hexdigest(), "bytes": 14}})

    def test_source_drift_fails_final_verification_without_modifying_real_source(self):
        from reddit_sna.artifacts import source_snapshot
        config, protocol = self.setup_config()
        calls = []
        def changed_snapshot():
            package, blobs, hashes = source_snapshot()
            calls.append(1)
            if len(calls) > 1:
                hashes["reddit_sna/artifacts.py"] = "0" * 64
            return package, blobs, hashes
        with patch("reddit_sna.artifacts.source_snapshot", side_effect=changed_snapshot), self.assertRaisesRegex(ValueError, "source changed"):
            run_synthetic_benchmark(config, protocol=protocol, dataset_ids=["dev-stable-easy-g11"])
        manifest = json.loads((config.run_directory / "manifest.json").read_text())
        self.assertEqual((manifest["status"], manifest["current_stage"]), ("failed", "verification"))
        self.assertFalse(manifest["integrity"]["source_unchanged"])
        self.assertEqual(manifest["integrity"]["source_changes"]["reddit_sna/artifacts.py"]["actual"], "0" * 64)
        self.assertTrue((config.run_directory / "evaluation/metadata.json").exists())

    def test_final_manifest_publication_error_cannot_leave_complete_run(self):
        from reddit_sna.artifacts import save_run_manifest
        config, protocol = self.setup_config()
        def fail_complete(run, manifest):
            if manifest["status"] == "complete":
                raise OSError("complete publication failed")
            save_run_manifest(run, manifest)
        with patch("reddit_sna.artifacts.save_run_manifest", side_effect=fail_complete), self.assertRaisesRegex(OSError, "complete publication failed"):
            run_synthetic_benchmark(config, protocol=protocol, dataset_ids=["dev-stable-easy-g11"])
        manifest = json.loads((config.run_directory / "manifest.json").read_text())
        self.assertEqual((manifest["status"], manifest["current_stage"]), ("failed", "manifest_publication"))
        self.assertTrue((config.run_directory / "evaluation/metadata.json").exists())
        self.assertEqual(manifest["error"]["type"], "OSError")

    def test_failed_manifest_fallback_keeps_original_exception_and_full_failed_record(self):
        from reddit_sna.artifacts import save_run_manifest
        config, protocol = self.setup_config()
        def fail_failure(run, manifest):
            if manifest["status"] == "failed":
                raise OSError("failed publication unavailable")
            save_run_manifest(run, manifest)
        with patch("reddit_sna.artifacts.save_run_manifest", side_effect=fail_failure), patch("reddit_sna.pipelines.detection_tracking.export_graph_dataset", side_effect=ValueError("original generation failure")), self.assertRaisesRegex(ValueError, "original generation failure"):
            run_synthetic_benchmark(config, protocol=protocol, dataset_ids=["dev-stable-easy-g11"])
        output = config.run_directory
        self.assertNotEqual(json.loads((output / "manifest.json").read_text())["status"], "complete")
        failed = json.loads((output / "failure.json").read_text())
        self.assertEqual((failed["status"], failed["current_stage"], failed["current_dataset"]),
                         ("failed", "generation", "dev-stable-easy-g11"))
        self.assertEqual(failed["error"]["message"], "original generation failure")
        self.assertEqual(failed["manifest_publication_error"], "failed publication unavailable")
        self.assertEqual(failed["stages"]["generation"]["status"], "failed")
        self.assertTrue(failed["files"])
        self.assertTrue(failed["source"]["files"])

    def test_keyboard_interrupt_retains_failed_status_and_does_not_invent_later_timing(self):
        config, protocol = self.setup_config()
        with patch("reddit_sna.pipelines.detection_tracking.export_graph_dataset", side_effect=KeyboardInterrupt()), self.assertRaises(KeyboardInterrupt):
            run_synthetic_benchmark(config, protocol=protocol, dataset_ids=["dev-stable-easy-g11"])
        manifest = json.loads((config.run_directory / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["error"]["type"], "KeyboardInterrupt")
        self.assertGreaterEqual(manifest["stages"]["generation"]["wall_seconds"], 0)
        self.assertIsNone(manifest["stages"]["evaluation"]["wall_seconds"])

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
        self.assertEqual(set(manifest["files"]), set(self.files(output)) - {"manifest.json"})
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
