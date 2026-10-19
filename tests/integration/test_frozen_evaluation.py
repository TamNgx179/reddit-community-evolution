"""Driver control-flow tests using identity-only stubs, never held-out labels or scores."""

from contextlib import contextmanager, ExitStack
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

from reddit_sna.artifacts import capture_run_provenance, run_file_inventory
from reddit_sna.benchmarks.freeze import BenchmarkFreeze
from reddit_sna.benchmarks.protocol import load_benchmark_protocol
from reddit_sna.config import ConfigError, load_config
from reddit_sna.contracts import PipelineName
from scripts import run_frozen_evaluation as driver
from tests.support import ProjectCase

ROOT = Path(__file__).resolve().parents[2]


class FrozenEvaluationDriverTests(ProjectCase):
    def setUp(self):
        super().setUp()
        config_path = self.config("detection-tracking")
        self.change(config_path, "seed = 42", "seed = 0")
        self.configured = load_config(config_path)
        self.frozen = self.root / "artifacts/detection-tracking/source-freeze"
        protocol = self.frozen / "config/protocol"
        protocol.mkdir(parents=True)
        for name in ("benchmark_week1.json", "benchmark_week1_protocol.json"):
            shutil.copyfile(ROOT / "configs" / name, protocol / name)
        (self.frozen / "config/run-config.toml").write_bytes(config_path.read_bytes())
        plan = load_benchmark_protocol(protocol / "benchmark_week1_protocol.json")
        from reddit_sna.benchmarks.config import dataset_schedule
        source, environment, _ = capture_run_provenance()
        manifest = {"fixture_role": "mocked control flow only; no generated held-out data or scores",
            "frozen_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "development": {"source_directory": str(self.root / "artifacts/earlier-development")},
            "source": source, "environment": environment,
            "schedules": {split: list(dataset_schedule(plan.benchmark, split)) for split in ("development", "evaluation")},
            "expected_counts": plan.protocol["expected_counts"],
            "frozen_protocol": {"archive": "config/protocol/benchmark_week1_protocol.json"},
            "files": run_file_inventory(self.frozen)}
        (self.frozen / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    @staticmethod
    def tree(path):
        return {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob("*") if p.is_file()}

    def mock_loader(self, directory):
        directory = Path(directory).resolve()
        content = (directory / "manifest.json").read_bytes()
        return BenchmarkFreeze(directory, json.loads(content), sha256(content).hexdigest(),
            load_benchmark_protocol(directory / "config/protocol/benchmark_week1_protocol.json"))

    @staticmethod
    def mock_generator(output, **kwargs):
        output.mkdir()
        (output / "metadata.json").write_text(json.dumps({"test_stub_only": True, "split": kwargs["split"]}), encoding="utf-8")

    @staticmethod
    def mock_detector(source, output, **kwargs):
        output.mkdir()
        (output / "metadata.json").write_text('{"test_stub_only": true}', encoding="utf-8")

    @staticmethod
    def mock_report(pairs, output):
        output.mkdir()
        (output / "stub-report.json").write_text('{"test_stub_only": true, "no_metric_values": true}', encoding="utf-8")
        return {"dataset_count": len(pairs), "metric_rows": len(pairs) * 6}

    @contextmanager
    def stubbed(self, **overrides):
        actions = {"load_benchmark_freeze": self.mock_loader, "export_graph_dataset": self.mock_generator,
                   "export_synthetic_detection": self.mock_detector, "export_detection_evaluation": self.mock_report,
                   "dependencies": lambda: None, "import_module": lambda name: None}
        actions.update(overrides)
        with ExitStack() as stack:
            mocks = {name: stack.enter_context(patch.object(driver, name, side_effect=action)) for name, action in actions.items()}
            yield mocks

    def execute(self, config=None):
        return driver.run_frozen_evaluation(config or self.configured, freeze=self.frozen)

    def test_invalid_config_rejects_before_freeze_or_algorithms(self):
        for bad in (replace(self.configured, pipeline=PipelineName.PREDICTION), replace(self.configured, seed=1),
                    replace(self.configured, seed=False), replace(self.configured, input_path=self.marker.parent),
                    replace(self.configured, output_root=self.root / "data/raw")):
            with self.subTest(config=bad), patch.object(driver, "load_benchmark_freeze") as frozen, self.assertRaises(ConfigError):
                self.execute(bad)
            frozen.assert_not_called()
        self.assertFalse(self.configured.run_directory.exists())

    def test_freeze_or_backend_failure_does_not_create_output(self):
        with self.stubbed(load_benchmark_freeze=lambda path: (_ for _ in ()).throw(ConfigError("frozen source mismatch"))) as mocks, self.assertRaisesRegex(ConfigError, "frozen source"):
            self.execute()
        mocks["export_graph_dataset"].assert_not_called()
        with self.stubbed(dependencies=lambda: (_ for _ in ()).throw(ImportError("graph unavailable"))) as mocks, self.assertRaisesRegex(ImportError, "graph unavailable"):
            self.execute()
        mocks["export_graph_dataset"].assert_not_called()
        self.assertFalse(self.configured.run_directory.exists())

    def test_toml_drift_future_freeze_and_overlap_reject_before_output(self):
        original = self.configured.source.read_bytes()
        self.configured.source.write_bytes(original + b"\n")
        with self.stubbed(), self.assertRaisesRegex(ConfigError, "TOML differs"):
            self.execute()
        self.configured.source.write_bytes(original)
        def future(path):
            frozen = self.mock_loader(path)
            frozen.manifest["frozen_at"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
            return frozen
        with self.stubbed(load_benchmark_freeze=future), self.assertRaisesRegex(ConfigError, "before the freeze"):
            self.execute()
        with self.stubbed(), self.assertRaisesRegex(ConfigError, "overlap"):
            self.execute(replace(self.configured, output_root=self.frozen))
        self.assertFalse(self.configured.run_directory.exists())

    def test_mocked_full_schedule_records_freeze_driver_and_no_overwrite(self):
        original = self.tree(self.frozen)
        with self.stubbed() as mocks:
            output = self.execute()
        manifest = json.loads((output / "manifest.json").read_bytes())
        self.assertEqual((manifest["status"], manifest["scope"], manifest["split"]), ("complete", "heldout-detection-evaluation", "evaluation"))
        self.assertEqual(manifest["actual_counts"], {"datasets": 18, "snapshots": 36, "snapshot_detector_runs": 108})
        self.assertTrue(manifest["evaluation_executed"])
        self.assertFalse(manifest["freeze_record_created"])
        self.assertEqual(manifest["tracking_status"], "not_implemented")
        self.assertEqual(len(mocks["export_graph_dataset"].call_args_list), 18)
        self.assertEqual({call.kwargs["generator_seed"] for call in mocks["export_graph_dataset"].call_args_list}, {101, 102, 103})
        self.assertTrue(all(call.kwargs["split"] == "evaluation" for call in mocks["export_graph_dataset"].call_args_list))
        self.assertEqual(sha256((output / manifest["driver"]["archive"]).read_bytes()).hexdigest(), manifest["driver"]["sha256"])
        self.assertEqual(self.tree(self.frozen), original)
        before = self.tree(output)
        with self.stubbed(), self.assertRaisesRegex(ConfigError, "run already exists"):
            self.execute()
        self.assertEqual(self.tree(output), before)
        self.assertFalse((output / "evaluation/detection_metrics.csv").exists(), "stubs must never fabricate actual scores")

    def test_mocked_second_detector_failure_keeps_partial_and_truth_stubs(self):
        seen = []
        def fail_second(source, output, **kwargs):
            seen.append(source.name)
            if len(seen) == 1:
                return self.mock_detector(source, output, **kwargs)
            output.mkdir()
            (output / "partial.txt").write_bytes(b"controlled test failure")
            raise ValueError("second stub detector failed")
        with self.stubbed(export_synthetic_detection=fail_second), self.assertRaisesRegex(ValueError, "second stub detector"):
            self.execute()
        manifest = json.loads((self.configured.run_directory / "manifest.json").read_bytes())
        self.assertEqual((manifest["status"], manifest["current_stage"]), ("failed", "detection"))
        self.assertEqual(manifest["progress_counts"], {"generated_datasets": 18, "detected_datasets": 1, "evaluated_datasets": 0})
        self.assertIn("inputs/detected/" + seen[1] + "/partial.txt", manifest["files"])
        self.assertFalse((self.configured.run_directory / "evaluation").exists())

    def test_mocked_wrong_report_counts_marks_root_failed(self):
        def wrong(pairs, output):
            self.mock_report(pairs, output)
            return {"dataset_count": 18, "metric_rows": 107}
        with self.stubbed(export_detection_evaluation=wrong), self.assertRaisesRegex(ConfigError, "report counts differ"):
            self.execute()
        manifest = json.loads((self.configured.run_directory / "manifest.json").read_bytes())
        self.assertEqual((manifest["status"], manifest["current_stage"]), ("failed", "evaluation"))
        self.assertEqual(manifest["progress_counts"]["evaluated_datasets"], 0)

    def test_mocked_driver_or_freeze_drift_fails_after_report_without_editing_real_source(self):
        for kind in ("driver", "freeze"):
            config = replace(self.configured, run_id="drift-" + kind)
            path, data = driver._driver_source()
            calls = []
            def changed_driver():
                calls.append(1)
                return path, data if len(calls) == 1 else data + b"\n"
            original_loads = []
            def changed_freeze(directory):
                frozen = self.mock_loader(directory)
                if Path(directory) == self.frozen:
                    original_loads.append(1)
                    if len(original_loads) > 1:
                        return replace(frozen, manifest_sha256="0" * 64)
                return frozen
            override = {"_driver_source": changed_driver} if kind == "driver" else {"load_benchmark_freeze": changed_freeze}
            with self.subTest(kind=kind), self.stubbed(**override), self.assertRaisesRegex(ConfigError, kind + " changed"):
                self.execute(config)
            self.assertEqual(json.loads((config.run_directory / "manifest.json").read_bytes())["status"], "failed")

    def test_cli_outside_repo_rejects_missing_freeze_and_existing_run(self):
        command = [sys.executable, str(ROOT / "scripts/run_frozen_evaluation.py"), "--config", str(self.configured.source),
                   "--freeze", str(self.root / "missing-freeze"), "--run-id", self.configured.run_id]
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertFalse(self.configured.run_directory.exists())
        self.configured.run_directory.mkdir()
        (self.configured.run_directory / "manifest.json").write_bytes(b'{"status":"started"}')
        before = self.tree(self.configured.run_directory)
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 2)
        self.assertIn("run already exists", result.stderr)
        self.assertEqual(self.tree(self.configured.run_directory), before)
