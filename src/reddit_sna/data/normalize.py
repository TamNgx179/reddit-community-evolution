"""Stream ConvoKit JSONL into a bounded-memory SQLite pilot store."""

from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import json
import math
import re
from pathlib import Path
import sqlite3
import zipfile

from reddit_sna.data.archive import utterance_member


def month_boundary(month: str) -> int:
    """Return the inclusive UTC timestamp of a strictly formatted YYYY-MM month."""
    if not isinstance(month, str) or not re.fullmatch(r"\d{4}-\d{2}", month):
        raise ValueError("month must use YYYY-MM")
    return int(datetime.strptime(month + "-01", "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def canonical_record(raw: dict, corpus: str, users: dict[str, str], end_stamp: int):
    """Do not serialize raw authors/text. Mapping is scoped to one dataset run.

    IDs follow first appearance in sorted archives, before the cutoff. Future
    rows are excluded before identity allocation, so appended future data has
    no influence on prior IDs. The private in-memory lookup is never persisted.
    """
    if not isinstance(raw, dict):
        raise ValueError("invalid_record")
    stamp = raw.get("timestamp")
    if type(stamp) not in (int, float) or not math.isfinite(stamp):
        raise ValueError("invalid_timestamp")
    date = datetime.fromtimestamp(stamp, timezone.utc)
    if stamp >= end_stamp:
        return None
    rid, root = raw.get("id"), raw.get("root", raw.get("conversation_id"))
    parent = raw.get("reply_to", raw.get("reply-to"))
    if not isinstance(rid, str) or not rid or not isinstance(root, str) or not root:
        raise ValueError("invalid_id_or_root")
    raw_id = rid.removeprefix("t1_").removeprefix("t3_")
    raw_root = root.removeprefix("t3_")
    is_post = parent is None and raw_id == raw_root
    if (rid.startswith("t3_") and not is_post) or (rid.startswith("t1_") and is_post):
        raise ValueError("inconsistent_post_id")
    if parent is not None:
        if not isinstance(parent, str) or not parent:
            raise ValueError("invalid_parent")
        if not parent.startswith(("t1_", "t3_")):
            parent = ("t3_" if parent == raw_root else "t1_") + parent
    author = raw.get("user", raw.get("speaker"))
    if isinstance(author, dict):
        author = author.get("id")
    if author is not None and not isinstance(author, str):
        raise ValueError("invalid_author")
    author = author.casefold() if author else None
    uid = None
    if author and author not in {"[deleted]", "[removed]", "automoderator"}:
        if author not in users:
            users[author] = f"u{len(users):09d}"
        uid = users[author]
    return (("t3_" if is_post else "t1_") + raw_id, uid, "t3_" + raw_root,
            parent, float(stamp), date.strftime("%Y-%m"), "post" if is_post else "comment", corpus)


def normalize_archives(paths: list[Path], target: Path, end_month: str, progress=print) -> dict:
    """Stream pre-cutoff metadata into a new SQLite store and return audit counts.

    Keep pre-pilot parents for lookup, exclude future rows before allocating IDs,
    reject conflicting duplicate records, and never persist raw author mappings.
    The caller owns failure status; an existing target is never overwritten."""
    if target.exists():
        raise FileExistsError("normalized store exists; choose a fresh run")
    end_stamp = month_boundary(end_month)
    users: dict[str, str] = {}
    totals = Counter()
    corpus_reports = []
    with closing(sqlite3.connect(target)) as db, db:
        db.execute("PRAGMA cache_size=-65536")
        db.execute("""CREATE TABLE records(
            id TEXT PRIMARY KEY, user_id TEXT, root TEXT, parent TEXT,
            timestamp REAL, month TEXT, kind TEXT, corpus TEXT)""")
        db.execute("CREATE TABLE provenance(key TEXT PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO provenance VALUES('identity_scope',?)", (target.parent.name,))
        db.execute("INSERT INTO provenance VALUES('end_month_exclusive',?)", (end_month,))
        for path in sorted(paths):
            counts = Counter()
            corpus = path.name.removesuffix(".corpus.zip")
            with zipfile.ZipFile(path) as archive, archive.open(utterance_member(archive)) as handle:
                for line in handle:
                    counts["raw_rows"] += 1
                    try:
                        row = canonical_record(json.loads(line), corpus, users, end_stamp)
                    except (ValueError, TypeError, OverflowError, OSError):
                        counts["invalid_rows"] += 1
                        continue
                    if row is None:
                        counts["at_or_after_end"] += 1
                        continue
                    try:
                        db.execute("INSERT INTO records VALUES(?,?,?,?,?,?,?,?)", row)
                        counts["inserted"] += 1
                        if row[1] is None:
                            counts["excluded_author_rows"] += 1
                    except sqlite3.IntegrityError:
                        previous = db.execute("SELECT * FROM records WHERE id=?", (row[0],)).fetchone()
                        if previous != row:
                            # Never print source payload, author or discussion text.
                            raise ValueError("conflicting duplicate record; normalization aborted") from None
                        counts["identical_duplicates"] += 1
                    if counts["raw_rows"] % 100000 == 0:
                        db.commit()
            db.commit()
            totals.update(counts)
            corpus_reports.append({"corpus": corpus, **counts})
            progress(f"normalize: {corpus} scanned={counts['raw_rows']} retained={counts['inserted']}", flush=True)
        db.execute("CREATE INDEX record_month ON records(month)")
        db.execute("CREATE INDEX record_parent ON records(parent)")
        monthly = [dict(zip(("month", "records", "posts", "valid_authors"), row)) for row in
                   db.execute("SELECT month,COUNT(*),SUM(kind='post'),COUNT(DISTINCT user_id) FROM records GROUP BY month ORDER BY month")]
    return {"status": "complete", "counts": dict(totals), "corpora": corpus_reports,
            "monthly_retained_metadata": monthly, "identity_scope": target.parent.name,
            "identity_policy": "first-seen ordinal, sorted archive order, pre-cutoff rows only; raw mapping not persisted",
            "known_limits": ["pseudonymous not anonymous", "additional bots not comprehensively excluded",
                             "pre-start rows retained only for metadata/history lookup"],
            "end_month_exclusive": end_month, "user_count": len(users)}


def open_readonly(path: Path) -> sqlite3.Connection:
    """Open an existing SQLite store in read-only mode; caller must close the connection."""
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
