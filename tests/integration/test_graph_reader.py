"""Independent graph/truth consumer accepts valid data and rejects corrupt packages."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

from reddit_sna.benchmarks.config import load_benchmark_config
from reddit_sna.benchmarks.io import export_graph_dataset
from tests.support import ProjectCase

ROOT = Path(__file__).resolve().parents[2]
READER = ROOT / "scripts/read_graph_dataset.py"


class GraphDatasetReaderTests(ProjectCase):
    def export(self, name, scenario="grow", **changes):
        benchmark = load_benchmark_config(ROOT / "configs/benchmark_week1.json")
        benchmark.update(changes)
        directory = self.root / name
        export_graph_dataset(directory, benchmark=benchmark, scenario=scenario, generator_seed=11)
        return directory

    def read(self, directory):
        return subprocess.run([sys.executable, "-I", str(READER), str(directory)], cwd=self.root,
                              capture_output=True, text=True, encoding="utf-8", timeout=20)

    def test_independent_reader_accepts_merge_split_dissolve_across_year_boundary(self):
        for case in ("merge", "split", "dissolve"):
            with self.subTest(case=case):
                directory = self.export(case, scenario=case, months=["2020-12", "2021-01"])
                before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
                result = self.read(directory)
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(result.stdout)
                self.assertIs(data["verified"], True)
                self.assertEqual(data["scenario"], case)
                self.assertEqual(data["observed_months"], ["2020-12", "2021-01"])
                self.assertEqual(data["counts"]["links"], 1 if case == "dissolve" else 3)
                self.assertEqual({p: p.read_bytes() for p in before}, before)

    def test_reader_rejects_hash_and_semantic_corruption_even_after_rehashing(self):
        directory = self.export("corruption")
        meta_path = directory / "metadata.json"
        original_meta = meta_path.read_bytes()
        edge = "snapshots/2020-01/R.csv"
        cases = [
            ("truth/events.csv", lambda s: s.replace(",grow\n", ",stable\n"), False, "SHA-256 mismatch"),
            ("truth/events.csv", lambda s: s.replace(",grow\n", ",stable\n"), True, "events differ"),
            ("truth/links.csv", lambda s: s.replace(",2020-02,C\n", ",2020-02,K\n"), True, "links differ"),
            ("truth/membership.csv", lambda s: s + s.splitlines()[1] + "\n", True, "memberships differ"),
            ("snapshots/2020-01/nodes.csv", lambda s: "\n".join(s.splitlines()[:-1]) + "\n", True, "nodes differ"),
            (edge, lambda s: s + s.splitlines()[1] + "\n", True, "duplicate or unsorted"),
            (edge, lambda s: s.replace(",1.0\n", ",nan\n", 1), True, "invalid edge weight"),
            (edge, lambda s: s.replace("2020-01,", "2020-02,", 1), True, "invalid edge month/endpoints"),
            (edge, lambda s: s.replace("u001,", "outside,", 1), True, "invalid edge month/endpoints"),
            ("truth/events.csv", lambda s: s.replace("reference_id,", "wrong_header,", 1), True, "wrong CSV header"),
            ("truth/events.csv", lambda s: s + "\n", True, "invalid CSV row"),
        ]
        for name, mutate, rehash, message in cases:
            path = directory / name
            original = path.read_bytes()
            with self.subTest(name=name, message=message):
                path.write_text(mutate(path.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
                if rehash:
                    meta = json.loads(original_meta)
                    meta["files"][name]["sha256"] = sha256(path.read_bytes()).hexdigest()
                    meta_path.write_text(json.dumps(meta), encoding="utf-8")
                before = path.read_bytes(), meta_path.read_bytes()
                result = self.read(directory)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn(message, result.stderr)
                self.assertEqual((path.read_bytes(), meta_path.read_bytes()), before)
            path.write_bytes(original)
            meta_path.write_bytes(original_meta)

    def test_reader_rejects_incomplete_identity_config_and_metadata_errors(self):
        directory = self.export("metadata")
        path = directory / "metadata.json"
        original = path.read_bytes()
        mutations = [
            (lambda m: m.update(status="started"), "not complete"),
            (lambda m: m.update(artifact_type="synthetic-sampler-diagnostic"), "not complete"),
            (lambda m: m.update(schema_version=True), "unsupported schema"),
            (lambda m: m.update(identity_scope="other"), "identity mismatch"),
            (lambda m: m.update(generator_seed=101), "seed/split mismatch"),
            (lambda m: m["counts"].update(events=9), "counts mismatch"),
            (lambda m: m["generator"]["config"].update(p_in=0.9), "config mismatch"),
            (lambda m: m.update(observed_months=["2020-01", "2020-03"]), "must be consecutive"),
            (lambda m: m["files"].update({"../outside.txt": {"sha256": "fake"}}), "inventory differs"),
        ]
        for mutate, message in mutations:
            meta = deepcopy(json.loads(original))
            mutate(meta)
            with self.subTest(message=message):
                path.write_text(json.dumps(meta), encoding="utf-8")
                before = path.read_bytes()
                result = self.read(directory)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn(message, result.stderr)
                self.assertEqual(path.read_bytes(), before)
        duplicate = original.decode("utf-8").replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1')
        path.write_text(duplicate, encoding="utf-8")
        result = self.read(directory)
        self.assertEqual(result.returncode, 2)
        self.assertIn("duplicate JSON key", result.stderr)
