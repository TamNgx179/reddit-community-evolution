import sqlite3
from contextlib import closing

from reddit_sna.data.normalize import canonical_record, month_boundary, normalize_archives
from tests.corpus_support import CorpusCase, record


class NormalizeTests(CorpusCase):
    def test_aliases_namespaces_and_no_private_payload(self):
        source = self.raw([record("p"), record("p", "synthetic_B", root="q", parent="q", modern=True),
                           record("d", "[deleted]", parent="p")])
        target = self.root / "pilot.sqlite"
        summary = normalize_archives([source], target, "2015-04", self.quiet)
        with closing(sqlite3.connect(target)) as db:
            rows = db.execute("SELECT * FROM records ORDER BY id").fetchall()
        self.assertEqual({r[0] for r in rows}, {"t3_p", "t1_p", "t1_d"})
        self.assertNotIn("synthetic_A", str(rows))
        self.assertNotIn("SYNTHETIC_TEXT", str(rows))
        self.assertEqual(summary["counts"]["excluded_author_rows"], 1)

    def test_exclusive_end_and_future_identity_invariance(self):
        users = {}
        end = month_boundary("2015-04")
        old = canonical_record(record("p"), "moderatepolitics", users, end)
        self.assertIsNone(canonical_record(record("f", "future_user", day="2015-04-01"), "moderatepolitics", users, end))
        self.assertEqual(len(users), 1)
        self.assertEqual(old, canonical_record(record("p"), "moderatepolitics", users, end))

    def test_duplicate_conflict_fails_and_identical_duplicate_is_counted(self):
        value = record("p")
        target = self.root / "one.sqlite"
        result = normalize_archives([self.raw([value, value])], target, "2015-04", self.quiet)
        self.assertEqual(result["counts"]["identical_duplicates"], 1)
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            normalize_archives([self.raw([value, record("p", "other")])], self.root / "two.sqlite", "2015-04", self.quiet)

    def test_bad_author_and_timestamp_are_reported(self):
        rows = [record("p"), record("a", 12), record("b")]
        rows[-1]["timestamp"] = True
        result = normalize_archives([self.raw(rows)], self.root / "bad.sqlite", "2015-04", self.quiet)
        self.assertEqual(result["counts"]["invalid_rows"], 2)
        with self.assertRaises(ValueError):
            month_boundary("2015-1")
