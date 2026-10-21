"""Versioned harder regime runs through real detection, freeze and tracking."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from reddit_sna.benchmarks.config import validate_benchmark_config
from reddit_sna.benchmarks.protocol import load_benchmark_protocol
from reddit_sna.pipelines.synthetic_week1 import run_demo
from tests.integration.test_group_delivery import prepare_project


class MidtermBenchmarkTests(unittest.TestCase):
    def test_versioned_regimes_cannot_be_mislabeled(self):
        root=Path(__file__).resolve().parents[2]
        easy=json.loads((root/'configs/benchmark_week1.json').read_text())
        harder=json.loads((root/'configs/benchmark_midterm.json').read_text())
        validate_benchmark_config(easy);validate_benchmark_config(harder)
        for original,new_difficulty in ((easy,'harder'),(harder,'easy')):
            changed=copy.deepcopy(original);changed['difficulty']=new_difficulty
            with self.assertRaises(ValueError):validate_benchmark_config(changed)
        changed=copy.deepcopy(harder);changed['generator']['p_out']=.02
        with self.assertRaises(ValueError):validate_benchmark_config(changed)
        self.assertEqual(load_benchmark_protocol(root/'configs/benchmark_midterm_protocol.json').benchmark,harder)

    def test_complete_fresh_harder_source_to_two_tracking_routes(self):
        import shutil
        project=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory(prefix='harder-midterm-') as tmp:
            root=Path(tmp);config=prepare_project(root)
            for name in ('benchmark_midterm.json','benchmark_midterm_protocol.json'):
                shutil.copy2(project/'configs'/name,root/'configs'/name)
            output=run_demo(config,'harder',protocol_path=root/'configs/benchmark_midterm_protocol.json')
            manifest=json.loads((output/'manifest.json').read_text())
            self.assertEqual(manifest['status'],'complete')
            self.assertEqual(manifest['figures'],8)
            self.assertEqual(len(manifest['tracking_summary']),4)
            dataset=output/'bundle/runs/evaluation/inputs/source/eval-grow-harder-g201/metadata.json'
            self.assertTrue(dataset.is_file())
            self.assertEqual(json.loads(dataset.read_text())['generator']['config']['p_out'],.10)
