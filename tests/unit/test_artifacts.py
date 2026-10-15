from dataclasses import replace
import json

from reddit_sna.artifacts import create_run_directory
from reddit_sna.config import ConfigError, load_config
from tests.support import ProjectCase


class ArtifactTests(ProjectCase):
    def test_new_run_records_provenance_without_claiming_metrics(self):
        config = load_config(self.config())
        run = create_run_directory(config)
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(run, config.run_directory.resolve())
        self.assertEqual(manifest["status"], "started")
        self.assertEqual(manifest["config"]["seed"], 42)
        self.assertEqual(manifest["config"]["input"]["kind"], "synthetic")
        self.assertTrue(manifest["python_version"])
        self.assertTrue(manifest["package_version"])
        self.assertEqual(sorted(path.name for path in run.iterdir()), ["manifest.json"])

    def test_repeated_run_preserves_manifest_and_results(self):
        config = load_config(self.config())
        run = create_run_directory(config)
        manifest = (run / "manifest.json").read_bytes()
        result = run / "metrics.json"
        result.write_text('{"test_fixture": true}', encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "already exists"):
            create_run_directory(config)
        self.assertEqual((run / "manifest.json").read_bytes(), manifest)
        self.assertEqual(result.read_text(encoding="utf-8"), '{"test_fixture": true}')

    def test_pipeline_namespaces_allow_same_run_id_without_collision(self):
        first = create_run_directory(load_config(self.config("prediction")))
        second = create_run_directory(load_config(self.config("detection-tracking")))
        self.assertNotEqual(first, second)
        self.assertEqual(first.name, second.name)
        self.assertTrue((first / "manifest.json").is_file())

    def test_destination_is_rechecked_immediately_before_writes(self):
        config = load_config(self.config())
        unsafe = replace(config, output_root=self.marker.parent)
        with self.assertRaises(ConfigError):
            create_run_directory(unsafe)
        self.assertEqual(self.marker.read_text(encoding="utf-8"), "synthetic input; preserve me")
        self.assertFalse((self.marker.parent / "prediction").exists())

    def test_preexisting_empty_run_directory_cannot_be_reused(self):
        config = load_config(self.config())
        config.run_directory.mkdir(parents=True)
        with self.assertRaisesRegex(ConfigError, "already exists"):
            create_run_directory(config)
        self.assertEqual(list(config.run_directory.iterdir()), [])

    def test_file_blocking_output_parent_is_preserved(self):
        config = load_config(self.config())
        config.output_root.mkdir()
        blocker = config.output_root / "prediction"
        blocker.write_text("keep existing file", encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "not a directory"):
            create_run_directory(config)
        self.assertEqual(blocker.read_text(encoding="utf-8"), "keep existing file")
