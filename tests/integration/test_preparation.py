from dataclasses import replace
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from reddit_sna.config import load_config
from reddit_sna.pipelines.preparation import run_preparation
from reddit_sna.data.archive import digest_file
from tests.corpus_support import CorpusCase, record


class PreparationPipelineTests(CorpusCase):
    @unittest.skipUnless(importlib.util.find_spec("leidenalg"), "install [graph]")
    def test_detect_inherits_actual_period_and_rejects_explicit_mismatch(self):
        self.raw()
        config = load_config(self.config('core'))
        source = run_preparation(config,start='2015-02',end='2015-04',corpora=('moderatepolitics',))
        output = run_preparation(replace(config,run_id='derived'),stage='detect',source_run=source)
        manifest = json.loads((output/'manifest.json').read_text())
        self.assertEqual(manifest['actual_months'],['2015-02','2015-03'])
        self.assertEqual(manifest['start_month'],'2015-02')
        with self.assertRaisesRegex(ValueError,'interval must match'):
            run_preparation(replace(config,run_id='mismatch'),stage='detect',source_run=source,start='2015-01')
        self.assertFalse((config.output_root/'core/mismatch').exists())

    def test_inconsistent_snapshot_metadata_rejected_before_output(self):
        self.raw()
        config = load_config(self.config('core'))
        normalized = run_preparation(config,stage='normalize',corpora=('moderatepolitics',))
        source = run_preparation(replace(config,run_id='graphs'),stage='snapshots',source_run=normalized)
        summary = json.loads((source/'snapshots.json').read_text())
        summary['months'] = summary['months'][:1]
        (source/'snapshots.json').write_text(json.dumps(summary))
        # Re-seal byte hashes to exercise semantic validation, not just corruption detection.
        manifest = json.loads((source/'manifest.json').read_text())
        manifest['artifact_hashes']['snapshots.json'] = digest_file(source/'snapshots.json')
        (source/'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'metadata months'):
            run_preparation(replace(config,run_id='invalid'),stage='detect',source_run=source)
        self.assertFalse((config.output_root/'core/invalid').exists())

    def test_advertised_actual_months_are_checked_against_content(self):
        self.raw()
        config = load_config(self.config('core'))
        normalized = run_preparation(config,stage='normalize',corpora=('moderatepolitics',))
        source = run_preparation(replace(config,run_id='graphs'),stage='snapshots',source_run=normalized)
        summary = json.loads((source/'snapshots.json').read_text())
        summary['actual_months'] = ['2015-01']
        (source/'snapshots.json').write_text(json.dumps(summary))
        manifest = json.loads((source/'manifest.json').read_text())
        manifest['artifact_hashes']['snapshots.json'] = digest_file(source/'snapshots.json')
        (source/'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'content/period'):
            run_preparation(replace(config,run_id='invalid'),stage='detect',source_run=source)
        self.assertFalse((config.output_root/'core/invalid').exists())

    @unittest.skipUnless(importlib.util.find_spec("leidenalg"), "install [graph]")
    def test_legacy_snapshot_migration_gets_explicit_protocol(self):
        self.raw()
        config = load_config(self.config('core'))
        source = run_preparation(config,corpora=('moderatepolitics',))
        summary = json.loads((source/'snapshots.json').read_text())
        for field in ('graph_protocol','graph_reference','snapshot_cohort_sha256','start_month','end_month_exclusive'):
            summary.pop(field)
        (source/'snapshots.json').write_text(json.dumps(summary))
        manifest = json.loads((source/'manifest.json').read_text())
        manifest['artifact_hashes']['snapshots.json'] = digest_file(source/'snapshots.json')
        (source/'manifest.json').write_text(json.dumps(manifest))
        output = run_preparation(replace(config,run_id='migrated'),stage='detect',source_run=source)
        result = json.loads((output/'detection.json').read_text())
        self.assertEqual(result['graph_protocol'],'legacy-reply-r-v1')
        self.assertEqual(len({m['runs'][0]['reference_id'] for m in result['months']}),1)

    def test_missing_graph_dependency_fails_before_reserving_output(self):
        self.raw()
        config = load_config(self.config("core"))
        with patch("reddit_sna.pipelines.preparation.dependencies", side_effect=ValueError("Leiden dependencies missing")):
            with self.assertRaisesRegex(ValueError, "dependencies missing"):
                run_preparation(config, corpora=("moderatepolitics",))
        self.assertFalse(config.run_directory.exists())

    def test_installed_cli_audit_and_corruption_failure(self):
        raw = self.raw()
        config = self.config("core")
        args = [sys.executable, "-m", "reddit_sna", "prepare", "--config", str(config),
                "--corpus", "moderatepolitics", "--stage", "audit"]
        env = dict(os.environ, PYTHONUTF8="1")
        result = subprocess.run(args, cwd=self.root, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / "artifacts/core/test-001/corpus_manifest.json").exists())
        raw.write_bytes(b"corrupted archive")
        result = subprocess.run(args + ["--run-id", "bad-zip"], cwd=self.root, env=env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        manifest = json.loads((self.root / "artifacts/core/bad-zip/manifest.json").read_text())
        self.assertEqual(manifest["status"], "failed")

    def test_independent_stages_and_source_hash_verification(self):
        self.raw()
        config = load_config(self.config("core"))
        normalized = run_preparation(config, stage="normalize", corpora=("moderatepolitics",))
        result = run_preparation(replace(config, run_id="graphs"), stage="snapshots", source_run=normalized)
        self.assertTrue((result / "snapshots.json").is_file())
        (normalized / "normalization.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            run_preparation(replace(config, run_id="tampered"), stage="snapshots", source_run=normalized)
        self.assertFalse((config.output_root / "core/tampered").exists())

    def test_conflicting_duplicate_records_failure_without_overwrite(self):
        self.raw([record("p"), record("p", "different")])
        config = load_config(self.config("core"))
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            run_preparation(config, stage="normalize", corpora=("moderatepolitics",))
        manifest = json.loads((config.run_directory / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "failed")
        with self.assertRaises(ValueError):
            run_preparation(config, stage="normalize", corpora=("moderatepolitics",))

    @unittest.skipUnless(importlib.util.find_spec("leidenalg"), "install [graph] for full preparation stages")
    def test_full_preparation_has_memberships_but_no_forecast_success_claim(self):
        self.raw()
        config = load_config(self.config("core"))
        result = run_preparation(config, corpora=("moderatepolitics",))
        manifest = json.loads((result / "manifest.json").read_text())
        self.assertEqual(manifest["completed_stages"], ["audit", "normalize", "snapshots", "detect"])
        self.assertEqual(manifest["forecast_status"], "not_implemented")
        self.assertTrue((result / "memberships/2015-01/membership-seed0.csv").is_file())
        self.assertFalse((result / "predictions.csv").exists())
