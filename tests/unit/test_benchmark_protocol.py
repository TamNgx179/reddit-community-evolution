"""Recipe/policy binding, split isolation and planning without evaluation access."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from reddit_sna.benchmarks.config import dataset_schedule
from reddit_sna.benchmarks.protocol import load_benchmark_protocol
from reddit_sna.config import ConfigError

ROOT = Path(__file__).resolve().parents[2]


class BenchmarkProtocolTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="reddit-protocol-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "protocol with spaces"
        self.root.mkdir()
        self.path = self.root / "benchmark_week1_protocol.json"
        self.recipe = self.root / "benchmark_week1.json"
        for path in (self.path, self.recipe):
            path.write_bytes((ROOT / "configs" / path.name).read_bytes())
        self.original = json.loads(self.path.read_text())

    def write(self, data):
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def rebind(self, config):
        self.recipe.write_text(json.dumps(config), encoding="utf-8")
        protocol = deepcopy(self.original)
        protocol["benchmark"]["sha256"] = sha256(self.recipe.read_bytes()).hexdigest()
        self.write(protocol)

    def test_repository_protocol_binds_18_datasets_per_split_and_216_planned_units(self):
        plan = load_benchmark_protocol(self.path)
        self.assertEqual(plan.benchmark_sha256, sha256(self.recipe.read_bytes()).hexdigest())
        self.assertEqual(plan.protocol_sha256, sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(plan.protocol["expected_counts"], {
            "development": {"datasets": 18, "snapshots": 36, "snapshot_detector_runs": 108},
            "evaluation": {"datasets": 18, "snapshots": 36, "snapshot_detector_runs": 108},
            "total": {"datasets": 36, "snapshots": 72, "snapshot_detector_runs": 216},
        })
        dev, held = [dataset_schedule(plan.benchmark, split) for split in ("development", "evaluation")]
        self.assertTrue({r["dataset_id"] for r in dev}.isdisjoint(r["dataset_id"] for r in held))
        self.assertTrue({r["generator_seed"] for r in dev}.isdisjoint(r["generator_seed"] for r in held))
        self.assertEqual(plan.protocol["ami_policy"]["empty_scored"], "null:empty_scored")
        self.assertFalse(plan.protocol["summary_policy"]["pool_detector_seeds"])

    def test_relocated_plan_reads_without_writes_and_returned_mutations_do_not_leak(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        plan = load_benchmark_protocol(self.path)
        self.assertEqual(plan.benchmark_path, self.recipe.resolve())
        plan.protocol["ami_policy"]["average_method"] = "max"
        plan.benchmark["generator"]["seeds"]["development"].append(99)
        again = load_benchmark_protocol(self.path)
        self.assertEqual(again.protocol["ami_policy"]["average_method"], "arithmetic")
        self.assertEqual(again.benchmark["generator"]["seeds"]["development"], [11, 12, 13])
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, before)

    def test_recipe_byte_drift_is_rejected_even_with_equivalent_json(self):
        self.recipe.write_bytes(self.recipe.read_bytes() + b"\n")
        with self.assertRaisesRegex(ConfigError, "SHA-256"):
            load_benchmark_protocol(self.path)

    def test_rebound_recipe_still_rejects_split_overlap_and_unsupported_detector_schedule(self):
        original = json.loads(self.recipe.read_text())
        variants = []
        overlap = deepcopy(original)
        overlap["generator"]["seeds"]["evaluation"] = [11, 102, 103]
        variants.append((overlap, "overlap"))
        gamma = deepcopy(original)
        gamma["detector"]["gamma"] = 2.0
        variants.append((gamma, "week-one detector"))
        canonical = deepcopy(original)
        canonical["detector"].update(seeds=[1, 0, 2], canonical_seed=1)
        variants.append((canonical, "week-one detector"))
        for config, reason in variants:
            self.rebind(config)
            with self.subTest(reason=reason), self.assertRaisesRegex(ConfigError, reason):
                load_benchmark_protocol(self.path)

    def test_wrong_ami_summary_or_split_policy_is_rejected_including_bool_integer_aliases(self):
        changes = [("ami_policy", "average_method", "max"), ("ami_policy", "empty_scored", "zero"),
                   ("ami_policy", "schema_version", True), ("summary_policy", "canonical_seed", False),
                   ("summary_policy", "pool_detector_seeds", True),
                   ("split_policy", "evaluation_access", "before_freeze")]
        for section, key, value in changes:
            protocol = deepcopy(self.original)
            protocol[section][key] = value
            self.write(protocol)
            with self.subTest(section=section, key=key), self.assertRaisesRegex(ConfigError, "policy"):
                load_benchmark_protocol(self.path)

    def test_expected_counts_reject_wrong_units_missing_groups_and_noninteger_counts(self):
        for change in ("pooled-datasets", "wrong-snapshots", "missing-split", "float-count", "bool-count"):
            protocol = deepcopy(self.original)
            counts = protocol["expected_counts"]
            if change == "pooled-datasets": counts["development"]["datasets"] = 54
            elif change == "wrong-snapshots": counts["total"]["snapshots"] = 36
            elif change == "missing-split": del counts["evaluation"]
            elif change == "float-count": counts["development"]["datasets"] = 18.0
            else: counts["development"]["datasets"] = True
            self.write(protocol)
            with self.subTest(change=change), self.assertRaisesRegex(ConfigError, "expected counts"):
                load_benchmark_protocol(self.path)

    def test_schema_unknown_keys_and_invalid_bindings_are_rejected(self):
        for change in ("schema", "bool-schema", "id", "extra", "missing", "binding-shape", "bad-hash"):
            protocol = deepcopy(self.original)
            if change == "schema": protocol["schema_version"] = 2
            elif change == "bool-schema": protocol["schema_version"] = True
            elif change == "id": protocol["protocol_id"] = "other"
            elif change == "extra": protocol["typo"] = True
            elif change == "missing": del protocol["ami_policy"]
            elif change == "binding-shape": protocol["benchmark"] = []
            else: protocol["benchmark"]["sha256"] = "X" * 64
            self.write(protocol)
            with self.subTest(change=change), self.assertRaises(ConfigError):
                load_benchmark_protocol(self.path)

    def test_absolute_parent_or_alternate_stream_paths_are_rejected(self):
        for name in ("../benchmark_week1.json", "..\\benchmark_week1.json", str(self.recipe.resolve()),
                     "benchmark_week1.json:stream", "", ".", "..", None):
            protocol = deepcopy(self.original)
            protocol["benchmark"]["file"] = name
            self.write(protocol)
            with self.subTest(name=name), self.assertRaisesRegex(ConfigError, "sibling filename"):
                load_benchmark_protocol(self.path)

    def test_missing_recipe_and_invalid_protocol_json_raise_config_errors(self):
        self.recipe.unlink()
        with self.assertRaises(ConfigError):
            load_benchmark_protocol(self.path)
        for content in ('{', '[]', '{"schema_version":1,"schema_version":1}', '{"value":NaN}'):
            self.path.write_text(content, encoding="utf-8")
            with self.subTest(content=content), self.assertRaises(ConfigError):
                load_benchmark_protocol(self.path)

    def test_cli_reports_a_plan_without_creating_artifacts_or_loading_metric_backends(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        command = [sys.executable, "-m", "reddit_sna.benchmarks.protocol", str(self.path)]
        completed = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        output = json.loads(completed.stdout)
        self.assertEqual((output["scope"], output["status"]), ("benchmark-plan-only", "planned"))
        self.assertEqual(output["planned_counts"]["total"]["snapshot_detector_runs"], 216)
        self.assertFalse(output["evaluation_executed"])
        self.assertFalse(output["freeze_record_created"])
        script = ("import sys; from pathlib import Path; from reddit_sna.benchmarks.protocol import load_benchmark_protocol; "
                  "load_benchmark_protocol(Path(sys.argv[1])); "
                  "assert not any(k.split('.')[0] in ('igraph','leidenalg','sklearn') for k in sys.modules)")
        fresh = subprocess.run([sys.executable, "-c", script, str(self.path)], cwd=self.root, capture_output=True, text=True, timeout=30)
        self.assertEqual(fresh.returncode, 0, fresh.stderr)
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, before)
        changed = deepcopy(self.original)
        changed["summary_policy"]["pool_detector_seeds"] = True
        self.write(changed)
        invalid = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=30)
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("summary policy", invalid.stderr)
        self.assertEqual(set(p.name for p in self.root.iterdir()), set(before))
