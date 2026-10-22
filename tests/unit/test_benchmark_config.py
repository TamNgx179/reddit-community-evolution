"""Check benchmark JSON, split isolation and the configuration-to-sampler recipe."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from reddit_sna.benchmarks.config import dataset_schedule, load_benchmark_config, validate_benchmark_config
from reddit_sna.benchmarks.dynamic import sample_snapshots
from reddit_sna.benchmarks.scenarios import build_memberships
from reddit_sna.config import ConfigError

CONFIG = Path(__file__).resolve().parents[2] / "configs/benchmark_week1.json"


class BenchmarkConfigTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="reddit-benchmark-config-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "benchmark.json"
        self.path.write_bytes(CONFIG.read_bytes())
        self.config = load_benchmark_config(self.path)

    def test_repository_defaults_plan_36_datasets_72_snapshots_216_detector_units(self):
        config = self.config
        self.assertEqual(config["months"], ["2020-01", "2020-02"])
        self.assertEqual(config["generator"]["seeds"], {"development": [11, 12, 13], "evaluation": [101, 102, 103]})
        self.assertEqual(config["generator"]["p_in"], 0.50)
        self.assertEqual(config["generator"]["p_out"], 0.02)
        self.assertEqual(config["detector"], {"gamma": 1.0, "seeds": [0, 1, 2], "canonical_seed": 0})
        dev, evaluation = dataset_schedule(config, "development"), dataset_schedule(config, "evaluation")
        self.assertEqual((len(dev), len(evaluation)), (18, 18))
        self.assertEqual((len(dev) + len(evaluation)) * len(config["months"]), 72)
        self.assertEqual(72 * len(config["detector"]["seeds"]), 216)

    def test_loading_and_planning_leave_input_objects_files_and_directories_unchanged(self):
        before = deepcopy(self.config)
        original = self.path.read_bytes()
        validate_benchmark_config(self.config)
        dataset_schedule(self.config, "development")
        self.assertEqual(self.config, before)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.root.iterdir()), [self.path])
        with self.assertRaises(ConfigError):
            load_benchmark_config(self.root / "missing.json")
        self.assertFalse((self.root / "missing.json").exists())

    def test_json_rejects_duplicates_nonstandard_numbers_and_malformed_input(self):
        for text in ("", "{", "[]", "\ufeff{}", '{"schema_version":1,"schema_version":1}',
                     '{"generator":{"p_in":0.5,"p_in":0.5}}', '{"p":NaN}', '{"p":Infinity}'):
            with self.subTest(text=text):
                self.path.write_text(text, encoding="utf-8")
                original = self.path.read_bytes()
                with self.assertRaises(ConfigError):
                    load_benchmark_config(self.path)
                self.assertEqual(self.path.read_bytes(), original)

    def test_unknown_missing_or_wrong_shape_tables_are_rejected(self):
        for path in ((), ("generator",), ("generator", "seeds"), ("detector",), ("ordering",)):
            for variant in ("unknown", "missing", "wrong_shape"):
                config = deepcopy(self.config)
                table = config
                for name in path:
                    table = table[name]
                if variant == "unknown":
                    table["typo"] = 1
                elif variant == "missing":
                    del table[next(iter(table))]
                elif path:
                    parent = config
                    for name in path[:-1]:
                        parent = parent[name]
                    parent[path[-1]] = []
                else:
                    config = []
                with self.subTest(path=path, variant=variant), self.assertRaises(ConfigError):
                    validate_benchmark_config(config)

    def test_unsupported_schema_months_cases_protocols_and_ordering_are_rejected(self):
        changes = (
            ("schema_version", True), ("schema_version", 2), ("protocol", "reddit-reply-v3"),
            ("difficulty", "hard"), ("months", ["2020-01", "2020-03"]),
            ("months", ["2020-02", "2020-01"]), ("months", ["2020-01"]),
            ("months", ["2020-1", "2020-02"]), ("months", [None, "2020-02"]),
            ("scenarios", ["stable"]), ("scenarios", ["stable"] * 6),
        )
        for key, value in changes:
            config = deepcopy(self.config)
            config[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_benchmark_config(config)
        for path, value in ((("generator", "sampler_version"), True), (("generator", "rng_protocol"), "other"),
                            (("ordering", "nodes"), "insertion_order")):
            config = deepcopy(self.config)
            config[path[0]][path[1]] = value
            with self.subTest(path=path), self.assertRaises(ConfigError):
                validate_benchmark_config(config)
        valid = deepcopy(self.config)
        valid["months"] = ["2020-12", "2021-01"]
        validate_benchmark_config(valid)

    def test_invalid_probabilities_weight_gamma_and_canonical_seed_are_rejected(self):
        variants = [("generator", name, value) for name in ("p_in", "p_out")
                    for value in (-0.1, 1.1, float("nan"), float("inf"), True, "0.5", None)]
        variants += [("generator", "weight", value) for value in (0, 2, True, "1.0")]
        variants += [("detector", "gamma", value) for value in (0, -1, float("nan"), float("inf"), True, "1", 10**500)]
        variants += [("detector", "canonical_seed", value) for value in (1, 99, False, "0")]
        for section, key, value in variants:
            config = deepcopy(self.config)
            config[section][key] = value
            with self.subTest(section=section, key=key, value=value), self.assertRaises(ConfigError):
                validate_benchmark_config(config)

    def test_seed_lists_reject_empty_duplicate_wrong_type_or_out_of_range_values(self):
        for target in ("development", "evaluation", "detector"):
            for value in ([], "11", [11, 11], [True], [-1], [2**32], [11.0], [None]):
                config = deepcopy(self.config)
                if target == "detector":
                    config["detector"]["seeds"] = value
                else:
                    config["generator"]["seeds"][target] = value
                with self.subTest(target=target, value=value), self.assertRaises(ConfigError):
                    validate_benchmark_config(config)

    def test_split_seeds_and_dataset_ids_are_disjoint_and_detector_repeats_are_not_datasets(self):
        config = deepcopy(self.config)
        config["generator"]["seeds"]["evaluation"].append(11)
        with self.assertRaisesRegex(ConfigError, "overlap"):
            validate_benchmark_config(config)
        dev, evaluation = dataset_schedule(self.config, "development"), dataset_schedule(self.config, "evaluation")
        self.assertEqual(len({row["dataset_id"] for row in (*dev, *evaluation)}), 36)
        self.assertTrue({row["generator_seed"] for row in dev}.isdisjoint(row["generator_seed"] for row in evaluation))
        self.assertEqual(dev[0]["dataset_id"], "dev-stable-easy-g11")
        self.assertEqual(evaluation[-1]["dataset_id"], "eval-dissolve-easy-g103")
        self.assertEqual(dataset_schedule(self.config, "development"), dev)
        config = deepcopy(self.config)
        config["detector"]["seeds"] = [0]
        self.assertEqual(dataset_schedule(config, "development"), dev)
        with self.assertRaises(ConfigError):
            dataset_schedule(self.config, "train")

    def test_loaded_parameters_drive_the_existing_stable_sampler_example(self):
        generator = self.config["generator"]
        users = {f"u{i:03d}" for i in range(1, 13)} | {f"u{i:03d}" for i in range(101, 113)}
        reference = "truth-dev-stable-easy-g11"
        rows = build_memberships("stable", reference, start_month=self.config["months"][0])
        args = dict(expected_reference=reference, expected_users_by_month={month: users for month in self.config["months"]},
                    generator_seed=generator["seeds"]["development"][0], p_in=generator["p_in"], p_out=generator["p_out"])
        snapshots = sample_snapshots(rows, **args)
        self.assertEqual([(s.month, len(s.nodes), len(s.edges)) for s in snapshots],
                         [("2020-01", 24, 76), ("2020-02", 24, 53)])
        for snapshot in sample_snapshots(rows, **dict(args, p_in=0, p_out=0)):
            self.assertEqual((len(snapshot.nodes), len(snapshot.edges)), (24, 0))

    def test_validation_cli_reports_only_a_plan_and_returns_two_for_invalid_config(self):
        command = [sys.executable, "-m", "reddit_sna.benchmarks.config", str(self.path)]
        completed = subprocess.run(command, cwd=self.root, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), {
            "scope": "benchmark-config", "status": "valid", "planned_datasets": {"development": 18, "evaluation": 18},
            "planned_snapshots": 72, "planned_snapshot_detector_runs": 216,
        })
        config = deepcopy(self.config)
        config["generator"]["seeds"]["evaluation"] = [11]
        self.path.write_text(json.dumps(config), encoding="utf-8")
        original = self.path.read_bytes()
        invalid = subprocess.run(command, cwd=self.root, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("overlap", invalid.stderr)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.root.iterdir()), [self.path])
