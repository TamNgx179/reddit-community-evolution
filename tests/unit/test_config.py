from reddit_sna.config import ConfigError, load_config
from tests.support import ProjectCase


class ConfigTests(ProjectCase):
    def test_paths_resolve_from_config_in_a_directory_with_spaces(self):
        config = load_config(self.config("core"))
        self.assertEqual(config.project_root, self.root.resolve())
        self.assertEqual(config.input_path, self.marker.parent.resolve())
        self.assertEqual(config.output_root, self.root.resolve() / "artifacts")
        self.assertFalse(config.output_root.exists())

    def test_both_synthetic_pipelines_need_no_reddit_input(self):
        self.marker.unlink()
        self.marker.parent.rmdir()
        for pipeline in ("prediction", "detection-tracking"):
            with self.subTest(pipeline=pipeline):
                config = load_config(self.config(pipeline))
                self.assertIsNone(config.input_path)
                self.assertEqual(config.pipeline.value, pipeline)

    def test_core_requires_existing_input_directory(self):
        path = self.config("core")
        self.change(path, '../data/raw', '../missing')
        with self.assertRaisesRegex(ConfigError, "does not exist"):
            load_config(path)
        self.change(path, '../missing', '../data/raw/synthetic.txt')
        with self.assertRaisesRegex(ConfigError, "directory"):
            load_config(path)

    def test_unknown_top_level_and_nested_fields_are_rejected(self):
        for old, new in (
            ('seed = 42', 'seed = 42\nsed = 1'),
            ('kind = "synthetic"', 'kind = "synthetic"\nextra = 1'),
            ('root = "../artifacts"', 'root = "../artifacts"\nextra = 1'),
        ):
            with self.subTest(new=new):
                path = self.config()
                self.change(path, old, new)
                with self.assertRaisesRegex(ConfigError, "unknown keys"):
                    load_config(path)

    def test_missing_and_wrong_table_types_are_rejected(self):
        for old, new in (
            ('seed = 42\n', ''),
            ('seed = 42', 'seed = 42\ninput = "bad"'),
        ):
            with self.subTest(new=new):
                path = self.config()
                self.change(path, old, new)
                with self.assertRaises(ConfigError):
                    load_config(path)

    def test_seed_and_schema_are_strict_integers(self):
        for old, new in (
            ('seed = 42', 'seed = true'),
            ('seed = 42', 'seed = -1'),
            ('seed = 42', 'seed = 4294967296'),
            ('schema_version = 1', 'schema_version = true'),
            ('schema_version = 1', 'schema_version = 2'),
        ):
            with self.subTest(new=new):
                path = self.config()
                self.change(path, old, new)
                with self.assertRaises(ConfigError):
                    load_config(path)

    def test_unknown_pipeline_and_wrong_input_kind_are_rejected(self):
        for old, new in (
            ('pipeline = "prediction"', 'pipeline = "other"'),
            ('kind = "synthetic"', 'kind = "reddit"'),
        ):
            with self.subTest(new=new):
                path = self.config()
                self.change(path, old, new)
                with self.assertRaises(ConfigError):
                    load_config(path)

    def test_invalid_toml_and_missing_config_are_clear_errors(self):
        path = self.config()
        path.write_text('pipeline = [', encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "cannot read TOML"):
            load_config(path)
        path.unlink()
        with self.assertRaisesRegex(ConfigError, "cannot read TOML"):
            load_config(path)

    def test_unsafe_or_reserved_run_ids_are_rejected(self):
        for run_id in ("", "..", "../outside", "a/b", "a\\b", "CON", "nul", "COM1", "LPT9", "a" * 65):
            with self.subTest(run_id=run_id):
                with self.assertRaisesRegex(ConfigError, "run_id"):
                    load_config(self.config(run_id=run_id))

    def test_override_run_id_does_not_modify_config_file(self):
        path = self.config()
        original = path.read_bytes()
        config = load_config(path, run_id="second-run")
        self.assertEqual(config.run_id, "second-run")
        self.assertEqual(path.read_bytes(), original)

    def test_output_cannot_escape_artifacts_or_overlap_data(self):
        for output in ("../data/raw", "../data/private", "..", "../reports", "../../outside"):
            with self.subTest(output=output):
                with self.assertRaises(ConfigError):
                    load_config(self.config(output=output))
        self.assertEqual(self.marker.read_text(encoding="utf-8"), "synthetic input; preserve me")

    def test_synthetic_input_is_also_protected(self):
        input_dir = self.root / "artifacts" / "fixture-input"
        input_dir.mkdir(parents=True)
        path = self.config(output="../artifacts/fixture-input")
        self.change(path, 'kind = "synthetic"', 'kind = "synthetic"\npath = "../artifacts/fixture-input"')
        with self.assertRaisesRegex(ConfigError, "overlap"):
            load_config(path)
