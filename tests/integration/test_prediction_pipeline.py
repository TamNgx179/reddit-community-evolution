"""Integration test for the prediction pipeline.

Tests:
- Full run produces all required files
- Same seed -> same samples.csv and predictions.csv hash
- Duplicate run-id is rejected
- Prediction keys match split keys
- Manifest has required fields and correct status
- B4 proba_* columns populated for non-fallback rows
"""
import csv
import hashlib
import json
import random
import string
import unittest
import tempfile
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _rand_id(prefix: str = "itest") -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}-{suffix}"


class TestPredictionPipeline(unittest.TestCase):
    """Use real synthetic execution in a temporary project, preserving user artifacts."""

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="prediction-integration-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.project_root = Path(cls.temporary.name)
        (cls.project_root / "configs").mkdir()
        (cls.project_root / "configs/prediction.toml").write_bytes(
            (Path(__file__).resolve().parents[2] / "configs/prediction.toml").read_bytes())
        cls.artifact_root = cls.project_root / "artifacts"
        cls.artifact_root.mkdir(parents=True, exist_ok=True)

    def _make_config(self, run_id: str, seed: int = 42):
        from reddit_sna.config import RunConfig, PipelineName
        return RunConfig(
            source=self.project_root / "configs" / "prediction.toml",
            project_root=self.project_root,
            pipeline=PipelineName.PREDICTION,
            seed=seed,
            input_kind="synthetic",
            input_path=None,
            output_root=self.artifact_root,
            run_id=run_id,
        )

    def test_full_run_produces_required_files(self):
        from reddit_sna.pipelines.prediction import run
        config = self._make_config(_rand_id("full"))
        run_dir = run(config)
        for fname in ("samples.csv", "feature_catalog.csv", "split.csv",
                      "predictions.csv", "manifest.json"):
            self.assertTrue((run_dir / fname).exists(), f"Missing: {fname}")

    def test_same_seed_same_hashes(self):
        from reddit_sna.pipelines.prediction import run
        c1 = self._make_config(_rand_id("hash"), seed=99)
        d1 = run(c1)
        c2 = self._make_config(_rand_id("hash"), seed=99)
        d2 = run(c2)
        self.assertEqual(
            _sha256(d1 / "samples.csv"), _sha256(d2 / "samples.csv"),
            "samples.csv differs with same seed"
        )
        self.assertEqual(
            _sha256(d1 / "predictions.csv"), _sha256(d2 / "predictions.csv"),
            "predictions.csv differs with same seed"
        )

    def test_duplicate_run_id_rejected(self):
        from reddit_sna.pipelines.prediction import run
        from reddit_sna.config import ConfigError
        run_id = _rand_id("dup")
        run(self._make_config(run_id))
        with self.assertRaises((ConfigError, FileExistsError)):
            run(self._make_config(run_id))

    def test_prediction_keys_match_split_keys(self):
        from reddit_sna.pipelines.prediction import run
        d = run(self._make_config(_rand_id("keys")))
        with (d / "split.csv").open(encoding="utf-8", newline="") as f:
            split_keys = {
                (r["reference_id"], r["feature_month"], r["community_id"], r["label_month"])
                for r in csv.DictReader(f)
            }
        with (d / "predictions.csv").open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                key = (row["reference_id"], row["feature_month"],
                       row["community_id"], row["label_month"])
                self.assertIn(key, split_keys, f"Prediction key {key} not in split.csv")

    def test_manifest_has_required_fields_and_status(self):
        from reddit_sna.pipelines.prediction import run
        d = run(self._make_config(_rand_id("mfst")))
        manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        for field in ("status", "data_kind", "table_schema", "seed",
                      "stage_status", "artifact_hashes"):
            self.assertIn(field, manifest, f"Missing: {field}")
        self.assertEqual(manifest["data_kind"], "synthetic")
        self.assertEqual(manifest["table_schema"], "prediction-table-v1")
        # While _stage_evaluation is a stub the status must NOT be "complete"
        self.assertEqual(
            manifest["status"], "complete_through_baselines",
            "Status must be 'complete_through_baselines' until Anh's stage merges"
        )

    def test_b4_proba_columns_populated(self):
        """B4 proba_* columns must be numeric for non-fallback rows."""
        from reddit_sna.pipelines.prediction import run
        from reddit_sna.contracts import Event
        d = run(self._make_config(_rand_id("prob")))
        proba_cols = [f"proba_{e.value}" for e in Event]
        n_b4_rows = 0
        n_populated = 0
        with (d / "predictions.csv").open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row["model"] != "B4_logreg":
                    continue
                if row.get("used_fallback", "").lower() == "false":
                    n_b4_rows += 1
                    total_proba = sum(
                        float(row[c]) for c in proba_cols
                        if row.get(c) not in (None, "", "None")
                    )
                    if abs(total_proba - 1.0) < 0.01:
                        n_populated += 1
        self.assertGreater(n_b4_rows, 0, "No B4 non-fallback rows in predictions.csv")
        self.assertEqual(
            n_b4_rows, n_populated,
            f"Only {n_populated}/{n_b4_rows} B4 rows have probas summing to 1.0"
        )


if __name__ == "__main__":
    unittest.main()
