"""Extend a verified cutoff store without re-normalizing its historical rows."""

from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import zipfile

from reddit_sna.data.normalize import canonical_record, month_boundary, open_readonly
from reddit_sna.data.archive import digest_file, utterance_member


def extend_study(paths, source, target, end_month, progress=print):
    """SQLite-backup a read-only source, then insert only newly available rows.

    Caller must verify the source inventory and unchanged archive hashes first.
    Stable account pseudonyms make this equivalent to full normalization at the
    later cutoff. Source bytes are checked again after extension and preserved.
    """
    source,target=Path(source),Path(target)
    if target.exists():
        raise FileExistsError('Extended study store already exists')
    old_hash=digest_file(source)
    with closing(open_readonly(source)) as before,closing(sqlite3.connect(target)) as db:
        provenance=dict(before.execute('SELECT key,value FROM provenance'))
        start=provenance.get('end_month_exclusive','')
        if provenance.get('identity_scope')!='study-author-sha256-v1' or not start<end_month:
            raise ValueError('Study extension needs a compatible earlier cutoff')
        lower,upper=month_boundary(start),month_boundary(end_month)
        before.backup(db)
        db.execute('PRAGMA cache_size=-65536')
        users,pseudonyms={},{}
        totals,reports=Counter(),[]
        for path in sorted(map(Path,paths)):
            corpus=path.name.removesuffix('.corpus.zip')
            counts=Counter()
            with zipfile.ZipFile(path) as archive,archive.open(utterance_member(archive)) as stream:
                for line in stream:
                    counts['raw_rows']+=1
                    try:
                        raw=json.loads(line)
                        stamp=raw.get('timestamp') if isinstance(raw,dict) else None
                        if type(stamp) not in (int,float):
                            raise ValueError('Invalid extension timestamp')
                        if stamp<lower:
                            counts['already_normalized_before_cutoff']+=1
                            continue
                        row=canonical_record(raw,corpus,users,upper)
                    except (ValueError,TypeError,OverflowError,OSError):
                        counts['invalid_rows']+=1
                        continue
                    if row is None:
                        counts['at_or_after_end']+=1
                        continue
                    if row[1] is not None:
                        if row[1] not in pseudonyms:
                            author=raw.get('user',raw.get('speaker'))
                            author=author.get('id') if isinstance(author,dict) else author
                            pseudonyms[row[1]]='u'+hashlib.sha256(('reddit-study-author-v1:'+author.casefold()).encode()).hexdigest()
                        row=(row[0],pseudonyms[row[1]],*row[2:])
                    try:
                        db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?,?)',row)
                        counts['inserted']+=1
                        counts['excluded_author_rows']+=int(row[1] is None)
                    except sqlite3.IntegrityError:
                        if db.execute('SELECT * FROM records WHERE id=?',(row[0],)).fetchone()!=row:
                            raise ValueError('Conflicting duplicate in extended study store') from None
                        counts['identical_duplicates']+=1
                    if counts['inserted'] and counts['inserted']%100000==0:
                        db.commit()
                db.commit()
                reports.append(dict(corpus=corpus,**counts))
                totals.update(counts)
                progress(f'study extend: {corpus} inserted={counts["inserted"]}',flush=True)
        db.execute("UPDATE provenance SET value=? WHERE key='end_month_exclusive'",(end_month,))
        db.execute("INSERT INTO provenance VALUES('extended_from_sha256',?)",(old_hash,))
        db.commit()
    if digest_file(source)!=old_hash:
        raise ValueError('Read-only extension source changed')
    return dict(status='complete',identity_scope='study-author-sha256-v1',end_month_exclusive=end_month,
        previous_cutoff=start,source_sha256=old_hash,counts=dict(totals),corpora=reports,
        scope='Counts describe extension scanning/insertion, not cumulative source records')
