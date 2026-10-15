"""Synthetic ConvoKit archives only; no real author or text fixtures."""

from datetime import datetime, timezone
import json
import zipfile

from tests.support import ProjectCase


def record(rid, author="synthetic_A", *, parent=None, root="p", day="2015-01-02", modern=False):
    value = {"id": rid, "timestamp": datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp(),
             "reply_to": parent, "text": "SYNTHETIC_TEXT_MUST_NOT_PERSIST", "meta": {"score": 99}}
    value.update({"speaker" if modern else "user": author,
                  "conversation_id" if modern else "root": root})
    return value


def archive(path, rows):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        handle.writestr("corpus/utterances.jsonl", "".join(json.dumps(row) + "\n" for row in rows))
    return path


class CorpusCase(ProjectCase):
    def raw(self, rows=None):
        rows = rows if rows is not None else [
            record("p", "synthetic_A", day="2014-12-31"),
            record("x", "synthetic_B", parent="p"),
            record("y", "synthetic_A", parent="x"),
        ]
        return archive(self.marker.parent / "moderatepolitics.corpus.zip", rows)

    @staticmethod
    def quiet(*args, **kwargs):
        pass
