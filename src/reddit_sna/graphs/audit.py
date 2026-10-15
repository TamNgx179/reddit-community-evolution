"""Corpus-month support and mutually exclusive reply outcomes."""

VALID_REPLY = """c.user_id IS NOT NULL AND p.user_id IS NOT NULL
    AND c.user_id!=p.user_id AND p.timestamp<=c.timestamp"""
REPLY_OUTCOME = """CASE
    WHEN c.parent IS NULL THEN 'no_parent_pointer'
    WHEN p.id IS NULL THEN 'missing_parent'
    WHEN c.user_id IS NULL THEN 'excluded_child_author'
    WHEN p.user_id IS NULL THEN 'excluded_parent_author'
    WHEN p.timestamp>c.timestamp THEN 'parent_after_child'
    WHEN c.user_id=p.user_id THEN 'self_reply'
    ELSE 'valid' END"""
OUTCOMES = ("no_parent_pointer", "missing_parent", "excluded_child_author",
            "excluded_parent_author", "parent_after_child", "self_reply", "valid")


def corpus_month_audit(db, month: str, corpora: tuple[str, ...]) -> list[dict]:
    """Return complete corpus-month support and exclusive reply outcomes.

    Attribute a reply to the child's corpus; its parent may belong elsewhere.
    Intersect endpoints with active authors for coverage. Author counts across
    corpora overlap and must not be summed as unique network users."""
    stats = {r[0]: r[1:] for r in db.execute("""SELECT corpus,COUNT(*),SUM(kind='post'),
        SUM(kind='comment'),SUM(user_id IS NULL) FROM records WHERE month=? GROUP BY corpus""", (month,))}
    active = {c: set() for c in corpora}
    endpoints = {c: set() for c in corpora}
    for corpus, uid in db.execute("SELECT DISTINCT corpus,user_id FROM records WHERE month=? AND user_id IS NOT NULL", (month,)):
        active[corpus].add(uid)
    for corpus, u, v in db.execute(f"""SELECT DISTINCT c.corpus,c.user_id,p.user_id
            FROM records c JOIN records p ON c.parent=p.id
            WHERE c.month=? AND c.kind='comment' AND {VALID_REPLY}""", (month,)):
        endpoints[corpus].update((u, v))
    outcomes = {c: dict.fromkeys(OUTCOMES, 0) for c in corpora}
    for corpus, reason, count in db.execute(f"""SELECT c.corpus,{REPLY_OUTCOME} outcome,COUNT(*)
            FROM records c LEFT JOIN records p ON c.parent=p.id
            WHERE c.month=? AND c.kind='comment' GROUP BY c.corpus,outcome""", (month,)):
        outcomes[corpus][reason] = count
    result = []
    for corpus in corpora:
        count, posts, comments, excluded = stats.get(corpus, (0, 0, 0, 0))
        result.append({"month": month, "corpus": corpus, "records": count,
                       "posts": posts, "comments": comments,
                       "excluded_author_records": excluded, "valid_author_records": count-excluded,
                       "active_authors": len(active[corpus]), "reply_endpoints": len(endpoints[corpus]),
                       "edge_covered_active_authors": len(active[corpus] & endpoints[corpus]),
                       "reply_coverage_active_authors": len(active[corpus] & endpoints[corpus])/len(active[corpus]) if active[corpus] else None,
                       "reply_outcomes": outcomes[corpus],
                       "valid_reply_events": outcomes[corpus]["valid"],
                       "support_status": "observed" if count else "no_observed_activity"})
    return result
