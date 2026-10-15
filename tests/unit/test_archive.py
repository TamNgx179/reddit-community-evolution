import hashlib
import zipfile

from reddit_sna.data.archive import audit_archives, selected_archives, utterance_member
from tests.corpus_support import CorpusCase


class ArchiveTests(CorpusCase):
    def test_hash_crc_and_no_extraction(self):
        source = self.raw()
        before = source.read_bytes()
        result = audit_archives([source], self.quiet)
        self.assertEqual(result["archives"][0]["sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(result["archives"][0]["crc"], "passed")
        self.assertEqual(source.read_bytes(), before)
        self.assertFalse((source.parent / "corpus").exists())

    def test_incomplete_or_unknown_selection_fails(self):
        self.raw()
        with self.assertRaises(ValueError):
            selected_archives(self.marker.parent)
        with self.assertRaises(ValueError):
            selected_archives(self.marker.parent, ("../../outside",))
        self.assertEqual(len(selected_archives(self.marker.parent, ("moderatepolitics",))), 1)

    def test_bad_archive_and_multiple_members_rejected(self):
        source = self.raw()
        source.write_bytes(b"corrupt zip")
        with self.assertRaises(zipfile.BadZipFile):
            audit_archives([source], self.quiet)
        with zipfile.ZipFile(source, "w") as handle:
            handle.writestr("one/utterances.jsonl", "{}")
            handle.writestr("two/utterances.jsonl", "{}")
        with zipfile.ZipFile(source) as handle, self.assertRaises(ValueError):
            utterance_member(handle)
