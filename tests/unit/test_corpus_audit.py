from reddit_sna.data.normalize import normalize_archives
from reddit_sna.graphs.snapshots import build_snapshots
from tests.corpus_support import CorpusCase, archive, record


class CorpusAuditTests(CorpusCase):
    def test_exclusive_outcomes_support_coverage_and_history(self):
        rows = [record('p', day='2014-12-31'),
                record('q', 'synthetic_C', root='q'),
                record('ok1', 'synthetic_B', parent='p'), record('ok2', 'synthetic_B', parent='p'),
                record('self', parent='p'), record('deleted', '[deleted]', parent='p'),
                record('x', '[deleted]', root='x'), record('to_deleted', 'synthetic_B', parent='t3_x'),
                record('missing', None, parent='absent'), record('no_pointer', 'synthetic_B'),
                record('too_early', 'synthetic_D', parent='t3_later'),
                record('later', root='later', day='2015-02-01'),
                record('bot', 'AutoModerator', parent='p')]
        database = self.root/'normalized.sqlite'
        normalize_archives([self.raw(rows)], database, '2015-04', self.quiet)
        result = build_snapshots(database, self.root/'graphs', '2015-01', '2015-04',
                                 corpora=('moderatepolitics', 'AskALiberal'))
        jan = next(r for r in result['corpus_month_audit'] if r['month']=='2015-01' and r['corpus']=='moderatepolitics')
        self.assertEqual(jan['reply_outcomes'], {'no_parent_pointer':1,'missing_parent':1,
                         'excluded_child_author':2,'excluded_parent_author':1,'parent_after_child':1,
                         'self_reply':1,'valid':2})
        self.assertEqual(sum(jan['reply_outcomes'].values()), jan['comments'])
        self.assertEqual(jan['reply_coverage_active_authors'], 0.5)
        self.assertEqual(jan['excluded_author_records'], 4)
        self.assertEqual(result['historical_metadata_before_start']['moderatepolitics'], 1)
        self.assertEqual(len(result['corpus_month_audit']), 6)
        empty = [r for r in result['corpus_month_audit'] if r['corpus']=='AskALiberal']
        self.assertTrue(all(r['support_status']=='no_observed_activity' and r['reply_coverage_active_authors'] is None for r in empty))
        for graph in result['months']:
            cells = [r for r in result['corpus_month_audit'] if r['month']==graph['month']]
            self.assertEqual(sum(r['valid_reply_events'] for r in cells), graph['reply_events'])
        self.assertTrue((self.root/'graphs/corpus_month_audit.csv').is_file())

    def test_cross_corpus_author_counts_are_not_additive(self):
        a = self.raw([record('p'), record('c','synthetic_B',parent='p')])
        b = archive(a.parent/'AskALiberal.corpus.zip', [record('q',root='q'), record('d','synthetic_C',root='q',parent='q')])
        database = self.root/'normalized.sqlite'
        normalize_archives([a,b], database, '2015-04', self.quiet)
        result = build_snapshots(database,self.root/'graphs','2015-01','2015-04')
        cells = [r for r in result['corpus_month_audit'] if r['month']=='2015-01']
        self.assertEqual(sum(r['active_authors'] for r in cells),4)
        self.assertEqual(result['months'][0]['active_authors'],3)
        self.assertEqual(sum(r['valid_reply_events'] for r in cells),2)

    def test_empty_retained_store_still_reports_declared_corpora(self):
        database = self.root/'normalized.sqlite'
        normalize_archives([self.raw([record('future', day='2015-04-01')])],database,'2015-04',self.quiet)
        result = build_snapshots(database,self.root/'graphs','2015-01','2015-04',corpora=('moderatepolitics',))
        self.assertEqual(len(result['corpus_month_audit']),3)
        self.assertTrue(all(r['records']==0 for r in result['corpus_month_audit']))
