"""Temporary synthetic project; never access the real Reddit dataset."""

import json
from pathlib import Path
import tempfile
import unittest


class ProjectCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="reddit-sna-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "project with spaces"
        (self.root / "configs").mkdir(parents=True)
        (self.root / "data" / "raw").mkdir(parents=True)
        self.marker = self.root / "data" / "raw" / "synthetic.txt"
        self.marker.write_text("synthetic input; preserve me", encoding="utf-8")

    def config(self, pipeline="prediction", *, run_id="test-001", output="../artifacts"):
        kind = "reddit" if pipeline == "core" else "synthetic"
        input_path = '\npath = "../data/raw"' if kind == "reddit" else ""
        path = self.root / "configs" / f"{pipeline}.toml"
        path.write_text(
            'schema_version = 1\n'
            f'pipeline = {json.dumps(pipeline)}\n'
            'project_root = ".."\n'
            'seed = 42\n'
            f'\n[input]\nkind = "{kind}"{input_path}\n'
            f'\n[output]\nroot = {json.dumps(output)}\nrun_id = {json.dumps(run_id)}\n',
            encoding="utf-8",
        )
        return path

    @staticmethod
    def change(path, old, new):
        text = path.read_text(encoding="utf-8")
        if old not in text:
            raise AssertionError(f"test setup cannot replace {old!r}")
        path.write_text(text.replace(old, new), encoding="utf-8")
