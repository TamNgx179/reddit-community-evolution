import json
import os
from pathlib import Path
import subprocess
import sys

from tests.support import ProjectCase


class CliTests(ProjectCase):
    def cli(self, *args):
        environment = dict(os.environ, PYTHONUTF8="1")
        environment.pop("PYTHONPATH", None)
        return subprocess.run(
            [sys.executable, "-m", "reddit_sna", *map(str, args)],
            cwd=self.root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )

    def test_help_and_pipeline_list_work_from_outside_repo(self):
        help_result = self.cli("--help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("check", help_result.stdout)
        listing = self.cli("pipelines")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertIn("core: prepare/forecast/week1 implemented", listing.stdout)
        self.assertIn("generic run remains planned", listing.stdout)
        self.assertIn("detection-tracking: generation/detection/tracking/synthetic-week1 implemented", listing.stdout)
        self.assertIn("prediction: table/split/baselines/evaluation implemented", listing.stdout)

    def test_config_check_reports_resolved_paths_without_writing(self):
        result = self.cli("check", "--config", self.config("core"))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["pipeline"], "core")
        self.assertEqual(output["pipeline_status"], "prepare_forecast_week1_available")
        self.assertEqual(output["generic_run_status"], "scaffold-only")
        self.assertEqual(Path(output["input"]["path"]), self.marker.parent.resolve())
        self.assertFalse((self.root / "artifacts").exists())

    def test_check_does_not_import_any_pipeline_entrypoint(self):
        config = self.config("prediction")
        code = (
            "import sys; from reddit_sna.cli import main; "
            f"result = main(['check', '--config', {str(config)!r}]); "
            "assert result == 0; "
            "assert not any(name in sys.modules for name in "
            "['reddit_sna.pipelines.core', 'reddit_sna.pipelines.detection_tracking', "
            "'reddit_sna.pipelines.prediction'])"
        )
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "-c", code], cwd=self.root,
            capture_output=True, text=True, encoding="utf-8", timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unimplemented_runs_fail_without_producing_artifacts(self):
        original = self.marker.read_bytes()
        for pipeline in ("core", "detection-tracking"):
            with self.subTest(pipeline=pipeline):
                result = self.cli("run", "--config", self.config(pipeline))
                self.assertEqual(result.returncode, 3, result.stderr)
                self.assertIn("Not implemented", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.root / "artifacts").exists())
        self.assertEqual(self.marker.read_bytes(), original)

    def test_invalid_config_and_missing_input_return_two_without_artifacts(self):
        path = self.config("unknown-pipeline")
        result = self.cli("check", "--config", path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown pipeline", result.stderr)
        core = self.config("core")
        self.change(core, '../data/raw', '../missing-input')
        result = self.cli("run", "--config", core)
        self.assertEqual(result.returncode, 2)
        self.assertIn("does not exist", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.root / "artifacts").exists())

    def test_run_id_override_and_invalid_cli_arguments(self):
        path = self.config()
        result = self.cli("check", "--config", path, "--run-id", "new-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["output"]["run_id"], "new-run")
        result = self.cli("check", "--config", path, "--run-id", "../outside")
        self.assertEqual(result.returncode, 2)
        result = self.cli("check")
        self.assertEqual(result.returncode, 2)

    def test_console_entrypoint_emits_utf8_under_legacy_encoding(self):
        launcher = Path(sys.executable).parent / (
            "reddit-sna.exe" if os.name == "nt" else "reddit-sna"
        )
        result = subprocess.run(
            [str(launcher), "pipelines"], cwd=self.root,
            env=dict(os.environ, PYTHONIOENCODING="cp1252"),
            capture_output=True, text=True, encoding="utf-8", timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Reddit data", result.stdout)
        self.assertIn("Synthetic graphs", result.stdout)

    def test_unicode_config_path_with_legacy_encoding(self):
        path = self.config()
        unicode_path = path.with_name("forecast-\u03bb.toml")
        path.rename(unicode_path)
        result = subprocess.run(
            [sys.executable, "-m", "reddit_sna", "check", "--config", str(unicode_path)],
            cwd=self.root, env=dict(os.environ, PYTHONIOENCODING="cp1252"),
            capture_output=True, text=True, encoding="utf-8", timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(json.loads(result.stdout)["config_path"]), unicode_path.resolve())
