"""Real SQLite, sealed source and detector evidence for the continuity audit."""

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from reddit_sna.cli import main
from reddit_sna.data.normalize import month_boundary
from reddit_sna.data.observability import member_observations
from reddit_sna.evaluation.temporal_protocol import months, PRIMARY
from reddit_sna.pipelines.longitudinal import audit_study, load_protocol, run_audit, seed_repeatability
from reddit_sna.pipelines.study_preparation import prepare_month, seal, verified
from reddit_sna.pipelines.study_resources import json_write
from reddit_sna.pipelines.study_samples import build_study_samples, read_csv, write_csv
from reddit_sna.reporting.longitudinal import audit_figures, read_audit, matched_architecture, render_audit
from reddit_sna.data.archive import digest_file

PROJECT = Path(__file__).parents[2]
PROTOCOL = PROJECT/'configs/continuity_audit.toml'


class ObservationTests(unittest.TestCase):
    def test_real_database_post_only_parent_only_outside_corpus_and_self_reply(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'store.sqlite'
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('CREATE TABLE records(id TEXT PRIMARY KEY,user_id TEXT,root TEXT,parent TEXT,timestamp REAL,month TEXT,kind TEXT,corpus TEXT)')
                records = [('p', 'parent', 'p', None, 1, '2017-06', 'post', 'A'),
                    ('c', 'child', 'p', 'p', 2, '2017-07', 'comment', 'A'),
                    ('post', 'post-only', 'post', None, 3, '2017-07', 'post', 'A'),
                    ('outside', 'outside', 'outside', None, 3, '2017-07', 'post', 'B'),
                    ('self', 'post-only', 'post', 'post', 4, '2017-07', 'comment', 'A')]
                db.executemany('INSERT INTO records VALUES(?,?,?,?,?,?,?,?)', records)
            result = member_observations(path, '2017-07', ('A',))
            self.assertEqual(result['authored'], {'child', 'post-only'})
            self.assertEqual(result['reply_endpoints'], {'child', 'parent'})
            self.assertEqual(result['posts'], {'post-only'})
            self.assertEqual(member_observations(path, '2017-08', ('A',))['records'], 0)
            with self.assertRaises(ValueError):
                member_observations(path, '2017-07', ('A', 'A'))

    def test_archived_matched_control_settings_keys_and_unavailability(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            selection = root/'stages/selection/attempt-001'
            evaluation = root/'stages/evaluation/attempt-001'
            selection.mkdir(parents=True)
            evaluation.mkdir(parents=True)
            def fixture(mismatch=None):
                definitions = {PRIMARY: dict(kind='activity', fields=['fixture'], settings=dict(C=1), hierarchical=True),
                    'A_flat_matched': dict(kind='activity', fields=['fixture'], settings=dict(C=1), hierarchical=False)}
                if mismatch == 'settings':
                    definitions['A_flat_matched']['settings']['C'] = 2
                if mismatch == 'unavailable':
                    del definitions['A_flat_matched']
                json_write(selection/'selection.json', dict(definitions=definitions))
                seal(selection, dict(status='complete', stage='selection'))
                json_write(root/'freeze.json', dict(selection=selection.relative_to(root).as_posix(),
                    selection_manifest_sha256=digest_file(selection/'complete.json')))
                rows = [dict(model=name, seed=42, feature_month='2017-12', community_id='c0',
                    reference_id='fixture', label_reference_id='fixture-label', label_month='2018-01', size=2,
                    y_true='stable', y_pred='stable', fallback=0) for name in definitions]
                if mismatch == 'keys':
                    rows[-1]['reference_id'] = 'different'
                (evaluation/'predictions.csv').unlink(missing_ok=True)
                write_csv(evaluation/'predictions.csv', rows)
                seal(evaluation, dict(status='complete', stage='evaluation'))
            fixture()
            actual = matched_architecture(root)
            self.assertEqual(actual['status'], 'retrospective_auxiliary')
            self.assertAlmostEqual(actual['macro_f1'][PRIMARY], 1/6)
            for mismatch in ('settings', 'keys'):
                fixture(mismatch)
                with self.assertRaises(ValueError):
                    matched_architecture(root)
            fixture('unavailable')
            self.assertEqual(matched_architecture(root)['status'], 'unavailable')


class AuditIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        cls.study = cls.base/'study'
        cls.store = cls.study/'development-store'
        cls.store.mkdir(parents=True)
        cls.protocol = load_protocol(PROTOCOL)
        cls.database = cls.store/'normalized.sqlite'
        with closing(sqlite3.connect(cls.database)) as db, db:
            db.execute('CREATE TABLE records(id TEXT PRIMARY KEY,user_id TEXT,root TEXT,parent TEXT,timestamp REAL,month TEXT,kind TEXT,corpus TEXT)')
            db.execute('CREATE TABLE provenance(key TEXT PRIMARY KEY,value TEXT)')
            db.executemany('INSERT INTO provenance VALUES(?,?)', [('identity_scope', 'study-author-sha256-v1'), ('end_month_exclusive', '2018-01')])
            db.execute('CREATE INDEX record_month ON records(month)')
            for month in months('2015-01', '2018-01'):
                stamp = month_boundary(month)
                rows = [(month+'p', 'a', month+'p', None, stamp, month, 'post', 'A'),
                    (month+'c', 'b', month+'p', month+'p', stamp+1, month, 'comment', 'A'),
                    (month+'q', 'z', month+'q', None, stamp, month, 'post', 'B')]
                db.executemany('INSERT INTO records VALUES(?,?,?,?,?,?,?,?)', rows)
        json_write(cls.store/'normalization.json', dict(corpora=[dict(corpus=c) for c in ('A', 'B')]))
        cls.reseal_store()
        cls.directories = {}
        for month in months('2015-01', '2018-01'):
            directory = cls.study/f'stages/month-{month}/attempt-001'
            prepare_month(cls.database, directory, month, corpora=('A', 'B'))
            cls.directories[month] = directory
        cls.samples = cls.study/'stages/development-samples/attempt-001'
        build_study_samples(cls.database, cls.directories, cls.samples, 'fixture-reference', corpora=('A', 'B'))
        cls.output = cls.base/'result'
        audit_study(cls.study, cls.output, cls.protocol)

    @classmethod
    def reseal_store(cls):
        (cls.store/'complete.json').unlink(missing_ok=True)
        seal(cls.store, dict(status='complete', stage='normalize', end='2018-01', identity_scope='study-author-sha256-v1'))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_complete_real_pipeline_denominators_and_readable_figures(self):
        data = read_audit(self.output)
        self.assertEqual(data['summary']['sources'], 36)
        self.assertEqual(data['summary']['horizon_rows'], 108)
        total = next(r for r in data['summary']['strata'] if r['dimension'] == 'all')
        self.assertEqual(total['counts'], dict(accepted_next_month=33, right_censored=3))
        self.assertEqual(len(data['repeatability']), 108)
        self.assertTrue(all(r['ari'] == '' for r in data['repeatability']))
        self.assertEqual(data['summary']['horizon_support'][2], dict(horizon=3, sources=36, observed=33, right_censored=3, coverage_unknown=0))
        report = render_audit({'Fixture': data}, dict(status='unavailable'))
        for statement in ('Human review remains pending', 'not confirmed social death', 'no-dynamics control', 'contains zero'):
            self.assertIn(statement, report)
        figures = audit_figures({'Fixture': data})
        self.assertEqual(set(figures), {'followup', 'observation', 'repeatability'})
        import matplotlib.pyplot as plt
        for figure in figures.values():
            figure.canvas.draw()
            plt.close(figure)

    def test_corrupt_seal_and_future_records_are_refused(self):
        source = self.samples/'features.csv'
        saved = source.read_bytes()
        try:
            source.write_bytes(saved+b'corrupt')
            with self.assertRaises(ValueError):
                audit_study(self.study, self.base/'corrupt', self.protocol)
        finally:
            source.write_bytes(saved)
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?,?)', ('future', 'a', 'future', None, month_boundary('2018-01'), '2018-01', 'post', 'A'))
        self.reseal_store()
        try:
            with self.assertRaisesRegex(ValueError, 'Future/final'):
                audit_study(self.study, self.base/'future', self.protocol)
        finally:
            with closing(sqlite3.connect(self.database)) as db, db:
                db.execute("DELETE FROM records WHERE id='future'")
            self.reseal_store()

    def test_duplicate_and_mixed_censored_reference_keys_are_refused(self):
        path = self.samples/'labels.csv'
        manifest = self.samples/'complete.json'
        saved, saved_manifest = path.read_bytes(), manifest.read_bytes()
        for mode in ('duplicate', 'mixed'):
            try:
                lines = saved.decode().splitlines()
                if mode == 'duplicate':
                    lines.append(lines[1])
                else:
                    lines[-1] = lines[-1].replace('fixture-reference', 'mixed-reference')
                path.write_text('\n'.join(lines)+'\n', encoding='utf-8')
                info = json.loads(saved_manifest)
                manifest.unlink()
                seal(self.samples, {k: v for k, v in info.items() if k != 'artifact_hashes'})
                with self.assertRaisesRegex(ValueError, 'Duplicate/final/mixed'):
                    audit_study(self.study, self.base/mode, self.protocol)
            finally:
                path.write_bytes(saved)
                manifest.write_bytes(saved_manifest)

    def test_changed_seed_statistic_is_rejected_and_undefined_preserved(self):
        directory = self.directories['2015-01']
        path = directory/'detection.json'
        saved = path.read_bytes()
        try:
            value = json.loads(saved)
            value['months'][0]['seed_pair_ARI'][0] = .123
            path.write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'does not reproduce'):
                seed_repeatability(directory, '2015-01', {'c0': {'a', 'b'}})
        finally:
            path.write_bytes(saved)

    def test_paths_protocol_cli_and_output_corruption_fail(self):
        with self.assertRaises(ValueError):
            run_audit(PROTOCOL, self.study, self.study/'unsafe', self.base)
        with self.assertRaises(ValueError):
            run_audit(PROTOCOL, self.study, self.base.parent/'outside', self.base)
        invalid = self.base/'bad.toml'
        invalid.write_text(PROTOCOL.read_text().replace('alpha = 0.5', 'alpha = 0.4'))
        with self.assertRaises(ValueError):
            load_protocol(invalid)
        self.assertEqual(main(['audit-continuity', '--protocol', str(invalid), '--study', str(self.study), '--output', str(self.base/'invalid')]), 2)
        path = self.output/'summary.json'
        saved = path.read_bytes()
        try:
            path.write_bytes(saved+b'corrupt')
            with self.assertRaises(ValueError):
                read_audit(self.output)
        finally:
            path.write_bytes(saved)
