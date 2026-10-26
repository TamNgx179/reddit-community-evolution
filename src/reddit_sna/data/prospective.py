"""Declared Cornell acquisition and normalization without changing old cohorts.

Content hashes identify actual bytes, not publisher-signed checksums. Raw input
remains local. Development normalization excludes future records at the adapter.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from urllib.parse import urlsplit
from urllib.request import urlopen
import zipfile

from reddit_sna.data.archive import audit_archives, digest_file, utterance_member
from reddit_sna.data.study import normalize_study
from reddit_sna.data.study_extension import extend_study
from reddit_sna.pipelines.study_preparation import seal, verified
from reddit_sna.pipelines.study_resources import json_write

HOST = 'zissou.infosci.cornell.edu'
PREFIX = '/convokit/datasets/subreddit-corpus/corpus-zipped/'


def validate_archive(name, item):
    """Restrict source names, destination filenames and public HTTPS origin."""
    url = urlsplit(item['url'])
    if (not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for c in name) or
        set(item) != {'url','bytes'} or type(item['bytes']) is not int or item['bytes'] <= 0 or
        url.scheme != 'https' or url.hostname != HOST or url.port is not None or
        url.username is not None or url.password is not None or url.query or url.fragment or
        not url.path.startswith(PREFIX) or url.path.split('/')[-1] != name+'.corpus.zip' or
        '..' in url.path.split('/')):
        raise ValueError('Unsafe or undeclared prospective archive')


def receive_archive(stream, target, expected_bytes, minimum_free_gib):
    """Stream once and preserve partial bytes if size, disk or CRC checks fail."""
    target = Path(target)
    partial = target.with_suffix(target.suffix+'.partial')
    if target.exists() or partial.exists():
        raise FileExistsError('Preserve existing archive or incomplete acquisition')
    count = 0
    with partial.open('xb') as output:
        while block := stream.read(4*1024**2):
            count += len(block)
            if count > expected_bytes:
                raise ValueError('Archive exceeds declared byte size')
            if shutil.disk_usage(target.parent).free < minimum_free_gib*2**30:
                raise RuntimeError('Acquisition minimum free disk reached')
            output.write(block)
    if count != expected_bytes:
        raise ValueError('Truncated or changed archive')
    with zipfile.ZipFile(partial) as archive:
        utterance_member(archive)
        if archive.testzip() is not None:
            raise ValueError('Prospective ZIP CRC failure')
    digest = digest_file(partial)
    partial.rename(target)
    return dict(bytes=count,sha256=digest,crc='passed')


def acquire(raw, archives, minimum_free_gib=12):
    """Acquire only the frozen sources and verify provenance on every replay."""
    raw = Path(raw)
    raw.mkdir(parents=True,exist_ok=True)
    for name,item in archives.items():
        validate_archive(name,item)
    remaining = sum(item['bytes'] for name,item in archives.items() if not (raw/(name+'.corpus.zip')).exists())
    if shutil.disk_usage(raw).free < minimum_free_gib*2**30+remaining:
        raise RuntimeError('Insufficient free space for declared acquisition')

    def one(name):
        item = archives[name]
        target,record = raw/(name+'.corpus.zip'),raw/(name+'.json')
        if target.exists():
            saved = json.loads(record.read_text(encoding='utf-8'))
            if (saved['url'] != item['url'] or target.stat().st_size != item['bytes'] or
                saved['sha256'] != digest_file(target)):
                raise ValueError('Existing prospective archive provenance differs')
            return saved
        print(f'prospective acquire: {name}, {item["bytes"]} bytes',flush=True)
        with urlopen(item['url'],timeout=120) as response:
            if urlsplit(response.geturl()).hostname != HOST:
                raise ValueError('Redirect outside declared Cornell origin')
            saved = receive_archive(response,target,item['bytes'],minimum_free_gib)
        saved.update(corpus=name,url=item['url'],completed_utc=datetime.now(timezone.utc).isoformat())
        json_write(record,saved)
        print(f'prospective acquire: {name} complete',flush=True)
        return saved

    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(one,archives))


def normalize(raw, destination, end, archives, source=None):
    """Seal the standard numeric store contract for this explicit new cohort."""
    raw,destination = Path(raw),Path(destination)
    paths = []
    for name,item in sorted(archives.items()):
        validate_archive(name,item)
        path = raw/(name+'.corpus.zip')
        record = json.loads((raw/(name+'.json')).read_text(encoding='utf-8'))
        if (record['url'] != item['url'] or path.stat().st_size != item['bytes'] or
            record['sha256'] != digest_file(path)):
            raise ValueError('Prospective source archive changed')
        paths.append(path)
    destination.mkdir(parents=True,exist_ok=False)
    if source is None:
        audit = audit_archives(paths)
        summary = normalize_study(paths,destination/'normalized.sqlite',end)
    else:
        source = Path(source)
        verified(source)
        audit = json.loads((source/'archive_audit.json').read_text(encoding='utf-8'))
        if [r['archive'] for r in audit['archives']] != [p.name for p in paths]:
            raise ValueError('Prospective extension corpus inventory changed')
        summary = extend_study(paths,source/'normalized.sqlite',destination/'normalized.sqlite',end)
    for path,record in zip(paths,audit['archives']):
        if digest_file(path) != record['sha256']:
            raise ValueError('Prospective input changed during normalization')
    json_write(destination/'archive_audit.json',audit)
    json_write(destination/'normalization.json',summary)
    return seal(destination,dict(status='complete',stage='normalize',end=end,
        identity_scope=summary['identity_scope'],corpora=list(archives)))
