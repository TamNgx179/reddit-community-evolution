"""Provenance remains useful when Git metadata is unavailable."""

from hashlib import sha256
import subprocess
import unittest
from unittest.mock import patch

from reddit_sna.artifacts import capture_run_provenance


class RunProvenanceTests(unittest.TestCase):
    def test_missing_git_preserves_source_and_only_records_allowlisted_environment(self):
        with patch("reddit_sna.artifacts.subprocess.run", return_value=subprocess.CompletedProcess([], 128, "", "no git")), patch.dict("os.environ", {"PHUC_SECRET_TEST": "do-not-record", "PYTHONHASHSEED": "137"}):
            source, environment, blobs = capture_run_provenance()
        self.assertEqual(source["git"], {"status": "unavailable", "repository": None,
            "revision": None, "branch": None, "working_tree": None})
        self.assertEqual(source["files"], {name: sha256(data).hexdigest() for name, data in blobs.items()})
        self.assertEqual(environment["python_hash_seed"], "137")
        self.assertEqual(set(environment), {"python_version", "python_implementation", "python_executable",
            "platform", "packages", "python_hash_seed"})
