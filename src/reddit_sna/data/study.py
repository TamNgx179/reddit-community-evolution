"""Streaming study metadata with stable, pseudonymous cross-cutoff identifiers.

These unkeyed hashes are linkable pseudonyms, not anonymization. Neither raw
authors nor text are persisted. Original pilot normalization remains unchanged.
"""

from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import zipfile

from reddit_sna.data.archive import utterance_member
from reddit_sna.data.normalize import canonical_record, month_boundary


def normalize_study(paths, target, end_month, progress=print):
    """Create a new store; exclude future rows before identity allocation.

    Stable pseudonyms allow development and later evaluation stores to share
    identities without retaining a private lookup. Archive order still controls
    validation only, never the identifier. Conflicting duplicate rows abort.
    """
    target = Path(target)
    if target.exists():
        raise FileExistsError("Study store already exists")
    cutoff = month_boundary(end_month)
    users, pseudonyms = {}, {}
    counts, reports = Counter(), []
    with closing(sqlite3.connect(target)) as db:
        db.execute("PRAGMA cache_size=-65536")
        db.execute("CREATE TABLE records(id TEXT PRIMARY KEY,user_id TEXT,root TEXT,parent TEXT,timestamp REAL,month TEXT,kind TEXT,corpus TEXT)")
        db.execute("CREATE TABLE provenance(key TEXT PRIMARY KEY,value TEXT)")
        db.executemany("INSERT INTO provenance VALUES(?,?)", [
            ("identity_scope", "study-author-sha256-v1"),
            ("end_month_exclusive", end_month),
            ("identity_policy", "linkable SHA256 namespace pseudonyms; not anonymized")])
        for path in sorted(map(Path, paths)):
            corpus = path.name.removesuffix(".corpus.zip")
            local = Counter()
            with zipfile.ZipFile(path) as archive, archive.open(utterance_member(archive)) as stream:
                for line in stream:
                    local["raw_rows"] += 1
                    try:
                        raw = json.loads(line)
                        row = canonical_record(raw, corpus, users, cutoff)
                    except (ValueError, TypeError, OverflowError, OSError):
                        local["invalid_rows"] += 1
                        continue
                    if row is None:
                        local["at_or_after_end"] += 1
                        continue
                    if row[1] is not None:
                        if row[1] not in pseudonyms:
                            author = raw.get("user", raw.get("speaker"))
                            author = author.get("id") if isinstance(author, dict) else author
                            pseudonyms[row[1]] = "u" + hashlib.sha256(
                                ("reddit-study-author-v1:" + author.casefold()).encode()).hexdigest()
                        row = (row[0], pseudonyms[row[1]], *row[2:])
                    try:
                        db.execute("INSERT INTO records VALUES(?,?,?,?,?,?,?,?)", row)
                        local["inserted"] += 1
                        local["excluded_author_rows"] += int(row[1] is None)
                    except sqlite3.IntegrityError:
                        if db.execute("SELECT * FROM records WHERE id=?", (row[0],)).fetchone() != row:
                            raise ValueError("Conflicting duplicate study record") from None
                        local["identical_duplicates"] += 1
                    if local["raw_rows"] % 100000 == 0:
                        db.commit()
                        progress(f"study normalize: {corpus} scanned={local['raw_rows']}", flush=True)
            db.commit()
            reports.append(dict(corpus=corpus, **local))
            counts.update(local)
        db.execute("CREATE INDEX record_month ON records(month)")
        db.execute("CREATE INDEX record_parent ON records(parent)")
        db.commit()
    return dict(status="complete", counts=dict(counts), corpora=reports,
                identity_scope="study-author-sha256-v1", end_month_exclusive=end_month,
                privacy="linkable pseudonyms; local metadata only; no raw author/text lookup")
