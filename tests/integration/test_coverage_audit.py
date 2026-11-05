"""Small sealed synthetic handoff, including parent-only graph endpoints."""

import json
from pathlib import Path
import tempfile
import unittest

from reddit_sna.contracts import next_month
from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.coverage_audit import run_coverage_audit
from reddit_sna.pipelines.study_preparation import seal
from reddit_sna.pipelines.study_samples import write_csv


def coverage_fixture(root):
    """Synthetic contracts only; never use these numbers as Reddit evidence."""
    root = Path(root)
    source = root/'samples'
    source.mkdir(parents=True)
    features, labels, graphs, month_hashes = [], [], {}, {}
    for month in ('2016-01', '2016-02', '2016-03'):
        directory = root/f'graph-{month}'
        members, edges = [], []
        for cid, users in [('a', ['a1', 'a2']), ('b', ['b1', 'b2', 'b3', 'b4'])]:
            members.extend(dict(month=month, community_id=cid, user_id=u) for u in users)
            edges.extend(dict(month=month, source_user_id=a, target_user_id=b, weight=1)
                         for a, b in zip(users, users[1:]))
            features.append(dict(reference_id='fixture-r', feature_month=month, community_id=cid,
                available_through_month=month, size=len(users), history_missing=int(month == '2016-01'), density=.5))
            final = month == '2016-03'
            eligible = not final and cid == 'a'
            labels.append(dict(reference_id='fixture-r', label_reference_id='fixture-l',
                feature_month=month, community_id=cid, label_month=next_month(month),
                eligible=int(eligible), label='grow' if eligible else '', size=len(users),
                reason='final_snapshot_censored' if final else 'one_to_one' if eligible else 'weak_overlap_unresolved'))
        for folder in (directory/f'memberships/{month}', directory/f'snapshots/{month}'):
            folder.mkdir(parents=True)
        write_csv(directory/f'memberships/{month}/membership-seed0.csv', members)
        write_csv(directory/f'snapshots/{month}/R.csv', edges)
        (directory/'snapshots.json').write_text(json.dumps(dict(months=[dict(month=month,
            reply_endpoints=6, active_authors=5, edge_covered_active_authors=4,
            parent_only_endpoints=2, observed_users=8, reply_coverage_observed_users=.75,
            reply_coverage_active_authors=.8)])), encoding='utf-8')
        seal(directory, dict(status='complete', month=month))
        month_hashes[month] = digest_file(directory/'complete.json')
        graphs[month] = directory
    write_csv(source/'features.csv', features)
    write_csv(source/'labels.csv', labels)
    seal(source, dict(status='complete', reference_id='fixture-r', label_reference_id='fixture-l',
                     months=list(graphs), input_month_manifests=month_hashes))
    return source, graphs


class CoverageAuditIntegrationTests(unittest.TestCase):
    def test_full_graph_and_coverage_exports_preserve_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, graphs = coverage_fixture(root)
            before = digest_file(source/'complete.json')
            out = root/'out'
            result = run_coverage_audit(source, out, '2016-03', month_directories=graphs)
            self.assertEqual(result['graph_status'], 'verified')
            self.assertEqual(result['totals']['coverage'], .5)
            self.assertAlmostEqual(result['totals']['member_month_coverage'], 1/3)
            self.assertEqual(result['totals']['censored'], 2)
            self.assertEqual(result['totals']['censored_member_months'], 6)
            self.assertEqual(before, digest_file(source/'complete.json'))
            manifest = json.loads((out/'manifest.json').read_text())
            for name, expected in manifest['artifact_hashes'].items():
                self.assertEqual(digest_file(out/name), expected)
            with self.assertRaises(ValueError):
                run_coverage_audit(source, out, '2016-03')

    def test_absent_graphs_remain_pending_instead_of_claimed_checked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, _ = coverage_fixture(root)
            result = run_coverage_audit(source, root/'out', '2016-03')
            self.assertEqual(result['status'], 'coverage_complete_graph_pending')
            self.assertTrue(result['missing_evidence'])

    def test_changed_table_and_unbound_month_fail_before_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, graphs = coverage_fixture(root)
            with (source/'features.csv').open('a') as stream:
                stream.write('\n')
            with self.assertRaisesRegex(ValueError, 'changed source table'):
                run_coverage_audit(source, root/'out', '2016-03')
            self.assertFalse((root/'out').exists())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, graphs = coverage_fixture(root)
            seal(graphs['2016-01'], dict(status='complete', month='2016-01', unrelated=True))
            with self.assertRaisesRegex(ValueError, 'not bound'):
                run_coverage_audit(source, root/'out', '2016-03', month_directories=graphs)

    def test_wrong_graph_denominator_and_community_sizes_fail(self):
        for field, value in [('reply_coverage_active_authors', 6/5), ('reply_endpoints', 7)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source, graphs = coverage_fixture(root)
                directory = graphs['2016-01']
                data = json.loads((directory/'snapshots.json').read_text())
                data['months'][0][field] = value
                (directory/'snapshots.json').write_text(json.dumps(data))
                seal(directory, dict(status='complete', month='2016-01'))
                meta = json.loads((source/'complete.json').read_text())
                meta['input_month_manifests']['2016-01'] = digest_file(directory/'complete.json')
                (source/'complete.json').write_text(json.dumps(meta))
                with self.assertRaises(ValueError):
                    run_coverage_audit(source, root/'out', '2016-03', month_directories=graphs)
