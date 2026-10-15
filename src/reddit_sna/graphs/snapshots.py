"""Monthly reply graphs with explicit loss and user-coverage accounting."""

import csv
import hashlib
from contextlib import closing
from pathlib import Path

from reddit_sna.contracts import next_month
from reddit_sna.data.normalize import open_readonly
from reddit_sna.graphs.audit import OUTCOMES, VALID_REPLY, corpus_month_audit
from reddit_sna.graphs.provenance import ORDERED_GRAPH_PROTOCOL, snapshot_inventory


def write_csv(path: Path, columns, rows) -> None:
    """Write a UTF-8 table exclusively; preserve existing files rather than overwrite them."""
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)


def build_snapshots(database: Path, output: Path, start: str, end: str, *, corpora=None) -> dict:
    """Build child-month directed replies and their symmetric user projection R.

    Read normalized metadata without modification. Parents may precede the pilot
    but must not follow the child timestamp. Isolates remain in users.csv and
    coverage denominators; only endpoints enter detection. Return graph hashes,
    monthly counts and an exhaustive corpus-month audit, including zero cells."""
    next_month(start)
    next_month(end)
    if start >= end:
        raise ValueError("snapshot interval must be nonempty")
    months = []
    month = start
    while month < end:
        months.append(month)
        month = next_month(month)
    with closing(open_readonly(database)) as db:
        identity = db.execute("SELECT value FROM provenance WHERE key='identity_scope'").fetchone()[0]
        cutoff = db.execute("SELECT value FROM provenance WHERE key='end_month_exclusive'").fetchone()[0]
        if end > cutoff:
            raise ValueError("snapshot interval exceeds normalized observation cutoff")
        observed_corpora = {r[0] for r in db.execute("SELECT DISTINCT corpus FROM records")}
        corpora = tuple(sorted(corpora if corpora is not None else observed_corpora))
        if not corpora or len(set(corpora)) != len(corpora) or not observed_corpora.issubset(corpora):
            raise ValueError("declared corpora must be unique and include all normalized corpora")
        historical = dict(db.execute("SELECT corpus,COUNT(*) FROM records WHERE month<? GROUP BY corpus", (start,)))
        output.mkdir(exist_ok=False)
        summaries = []
        corpus_audit = []
        for month in months:
            db.execute("DROP TABLE IF EXISTS temp.month_replies")
            db.execute(f"""CREATE TEMP TABLE month_replies AS
                SELECT c.user_id source,p.user_id target,COUNT(*) weight
                FROM records c JOIN records p ON c.parent=p.id
                WHERE c.month=? AND c.kind='comment' AND {VALID_REPLY}
                GROUP BY c.user_id,p.user_id""", (month,))
            directed = db.execute("SELECT source,target,weight FROM month_replies ORDER BY source,target").fetchall()
            undirected = db.execute("""SELECT MIN(source,target) u,MAX(source,target) v,SUM(weight)
                FROM month_replies GROUP BY u,v ORDER BY u,v""").fetchall()
            endpoints = {uid for row in directed for uid in row[:2]}
            active = {row[0] for row in db.execute("SELECT DISTINCT user_id FROM records WHERE month=? AND user_id IS NOT NULL", (month,))}
            universe = active | endpoints
            corpus_audit.extend(corpus_month_audit(db, month, corpora))
            losses = db.execute("""SELECT COUNT(*),
                SUM(c.parent IS NULL),SUM(c.parent IS NOT NULL AND p.id IS NULL),
                SUM(p.timestamp>c.timestamp),SUM(c.user_id IS NULL OR p.user_id IS NULL),
                SUM(c.user_id=p.user_id),SUM(p.month<?)
                FROM records c LEFT JOIN records p ON c.parent=p.id
                WHERE c.month=? AND c.kind='comment'""", (start, month)).fetchone()
            month_dir = output / month
            month_dir.mkdir()
            write_csv(month_dir / "directed_R.csv", ["month", "source_user_id", "target_user_id", "weight"],
                      ((month, *row) for row in directed))
            write_csv(month_dir / "R.csv", ["month", "source_user_id", "target_user_id", "weight"],
                      ((month, *row) for row in undirected))
            write_csv(month_dir / "users.csv", ["user_id", "authored_in_month", "has_reply_edge"],
                      ((uid, int(uid in active), int(uid in endpoints)) for uid in sorted(universe)))
            # Ordinal pseudonyms can change when a later normalization cutoff
            # allocates users earlier in another archive. Order the detector by
            # a stable per-user anchor known through this month, not by that ID.
            anchors = dict(db.execute("""SELECT user_id,MIN(id) FROM records
                WHERE month<=? AND user_id IS NOT NULL GROUP BY user_id""", (month,)))
            write_csv(month_dir / "node_order.csv", ["month", "user_id", "order_key"],
                      ((month, uid, hashlib.sha256(("causal-record-anchor-v1:"+anchors[uid]).encode()).hexdigest())
                       for uid in sorted(endpoints)))
            summaries.append({"month": month, "graph_id": f"{identity}:R:{month}",
                              "directed_pairs": len(directed), "undirected_edges": len(undirected),
                              "reply_events": sum(row[2] for row in directed),
                              "active_authors": len(active), "reply_endpoints": len(endpoints),
                              "edge_covered_active_authors": len(active & endpoints),
                              "reply_coverage_active_authors": len(active & endpoints)/len(active) if active else None,
                              "parent_only_endpoints": len(endpoints-active), "observed_users": len(universe),
                              "isolates": len(universe-endpoints),
                              "reply_coverage_observed_users": len(endpoints)/len(universe) if universe else None,
                              "comment_records": losses[0],
                              **{k: v or 0 for k, v in zip(
                                  ("no_parent_pointer", "missing_parent", "parent_after_child", "excluded_author_incidence",
                                   "self_reply_incidence", "parent_before_pilot"), losses[1:])},
                              "loss_count_policy": "incidence counters may overlap; valid event total reported separately",
                              "weight_definition": "R_uv=directed_reply_count_uv+directed_reply_count_vu",
                              "cutoff": f"end of {month} UTC"})
    audit_columns = ["month", "corpus", "records", "posts", "comments", "excluded_author_records",
                     "active_authors", "edge_covered_active_authors", "reply_coverage_active_authors",
                     "valid_reply_events", "support_status"]
    write_csv(output / "corpus_month_audit.csv", audit_columns + list(OUTCOMES),
              ([row[c] for c in audit_columns] + [row["reply_outcomes"][c] for c in OUTCOMES]
               for row in corpus_audit))
    inventory = snapshot_inventory(output, protocol=ORDERED_GRAPH_PROTOCOL)
    for summary, graph in zip(summaries, inventory["month_graphs"]):
        summary["graph_sha256"] = graph["graph_sha256"]
        summary["graph_id"] = f"{identity}:{ORDERED_GRAPH_PROTOCOL}:{summary['month']}:{graph['graph_sha256']}"
    return {"status": "complete", "schema_version": 2, "identity_scope": identity,
            **inventory, "months": summaries, "declared_corpora": list(corpora),
            "historical_metadata_before_start": {c: historical.get(c, 0) for c in corpora},
            "node_order_policy": "SHA256(causal-record-anchor-v1: + MIN(record id authored through snapshot month)); canonical edge-index ordering",
            "corpus_month_audit": corpus_audit,
            "audit_policy": {"attribution": "comment's corpus; parent may be outside corpus",
                             "coverage": "active authors in corpus-month incident to valid replies attributed to that corpus / active authors in corpus-month",
                             "reply_outcomes": "exclusive priority order: no parent, missing parent, excluded child, excluded parent, future parent, self, valid; sum equals comments",
                             "author_counts": "unique within each corpus-month; not additive across corpora",
                             "incidence_counters": "monthly legacy incidence counters can overlap; do not sum as losses"}}
