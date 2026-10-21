"""Contract and filesystem checks for complete truth dataset exports."""

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reddit_sna.benchmarks.io import export_truth_fixture


class TruthFixtureExportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="reddit-truth-export-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def export(self, name, **overrides):
        args = dict(scenario="grow", dataset_id="dev-grow-easy-g11", generator_seed=11)
        args.update(overrides)
        return export_truth_fixture(self.root / name, **args)

    @staticmethod
    def files(root):
        return {path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*") if path.is_file()}

    def test_complete_metadata_covers_every_csv_and_records_seed_role(self):
        for scenario, count in (("stable", 48), ("grow", 54)):
            with self.subTest(scenario=scenario):
                meta = self.export(scenario, scenario=scenario, dataset_id=f"dev-{scenario}-easy-g11")
                root = self.root / scenario
                self.assertEqual(json.loads((root / "metadata.json").read_text(encoding="utf-8")), meta)
                self.assertEqual(meta["status"], "complete")
                self.assertEqual(meta["observed_months"], ["2020-01", "2020-02"])
                self.assertEqual(meta["generator"]["seed"], 11)
                self.assertIs(meta["generator"]["seed_used_for_truth"], False)
                self.assertEqual(meta["counts"]["memberships"], count)
                self.assertEqual(meta["counts"]["events"], 2)
                self.assertEqual(meta["counts"]["links"], 2)
                self.assertEqual(meta["detector_references"], {})
                self.assertTrue(meta["environment"]["python_version"])
                self.assertTrue(meta["environment"]["package_version"])
                files = self.files(root)
                self.assertEqual(set(files), set(meta["files"]) | {"metadata.json"})
                self.assertEqual(len(meta["files"]), 5)
                for name, info in meta["files"].items():
                    self.assertEqual(info["sha256"], sha256(files[name]).hexdigest())

    def test_same_configuration_repeats_data_and_metadata_bytes_in_new_outputs(self):
        for scenario in ("stable", "grow"):
            with self.subTest(scenario=scenario):
                self.export(scenario + "-one", scenario=scenario)
                self.export(scenario + "-two", scenario=scenario)
                self.assertEqual(self.files(self.root / (scenario + "-one")),
                                 self.files(self.root / (scenario + "-two")))

    def test_existing_complete_or_empty_destination_is_preserved(self):
        self.export("complete")
        before = self.files(self.root / "complete")
        with self.assertRaises(FileExistsError):
            self.export("complete")
        self.assertEqual(self.files(self.root / "complete"), before)
        (self.root / "empty").mkdir()
        with self.assertRaises(FileExistsError):
            self.export("empty")
        self.assertEqual(list((self.root / "empty").iterdir()), [])

    def test_invalid_arguments_create_no_output(self):
        invalid = [dict(generator_seed=seed) for seed in (-1, True, 2**32, "11")]
        invalid += [dict(dataset_id=value) for value in ("../escape", "CON", "", "name/child")]
        invalid += [dict(scenario=scenario) for scenario in ("shrink", "merge", "split", "dissolve")]
        invalid += [dict(start_month="2020-13")]
        for index, overrides in enumerate(invalid):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.export(f"invalid-{index}", **overrides)
            self.assertFalse((self.root / f"invalid-{index}").exists())

    def test_write_failure_keeps_partial_output_without_complete_metadata(self):
        from reddit_sna.benchmarks import io
        original = io._write_rows

        def fail_on_links(path, columns, rows):
            if path.name == "links.csv":
                raise OSError("simulated links write failure")
            return original(path, columns, rows)

        with patch.object(io, "_write_rows", side_effect=fail_on_links):
            with self.assertRaisesRegex(OSError, "simulated"):
                self.export("partial")
        self.assertTrue((self.root / "partial/truth/membership.csv").is_file())
        self.assertFalse((self.root / "partial/metadata.json").exists())
