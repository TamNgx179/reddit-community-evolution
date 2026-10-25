"""Acquire only the declared external-cohort archives with byte/CRC provenance.

Observed hashes identify downloaded bytes, not publisher-signed checksums.
The coordinator locks the protocol before acquisition. Failed partial files
are retained; original project data and completed archives are never replaced.
"""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import urlopen
import zipfile

from reddit_sna.data.archive import digest_file, utterance_member

BASE = 'https://zissou.infosci.cornell.edu/convokit/datasets/subreddit-corpus/corpus-zipped/'
ARCHIVES = {
    'AustralianPolitics': ('AtlantaTheaterGroup~-~AutoHotkey/', 30990309),
    'CanadaPolitics': ('Calgary26~-~CanadaPolitics/', 313511946),
    'ukpolitics': ('uberfakesMO~-~ukpolitics/', 1094426114),
}
CORPORA = tuple(ARCHIVES)


def declared_paths(raw, corpora):
    """Resolve the exact safe allowlist, never arbitrary names or paths."""
    if tuple(corpora) != CORPORA:
        raise ValueError('Confirmation requires the fixed three-corpus allowlist')
    root = Path(raw).resolve()
    paths = [root / f'{name}.corpus.zip' for name in corpora]
    if any(p.parent != root for p in paths):
        raise ValueError('Unsafe confirmation archive path')
    if any(not p.is_file() for p in paths):
        raise ValueError('Missing declared confirmation archive')
    return paths


def acquire(raw, minimum_free_gib=12):
    """Stream fixed-size HTTPS archives and preserve incomplete attempts.

    Completed files require matching local provenance on replay. No historical
    corpus is silently substituted if one of the declared inputs is unavailable.
    """
    raw = Path(raw).resolve()
    raw.mkdir(parents=True, exist_ok=True)
    remaining = sum(size for name, (_, size) in ARCHIVES.items()
                    if not (raw / f'{name}.corpus.zip').exists())
    if shutil.disk_usage(raw).free < minimum_free_gib * 2**30 + remaining:
        raise RuntimeError('Insufficient free space for the declared downloads')

    def download(name):
        folder, size = ARCHIVES[name]
        path = raw / f'{name}.corpus.zip'
        record = raw / f'{name}.json'
        url = BASE + folder + path.name
        if path.exists():
            if not record.is_file():
                raise ValueError('Existing archive lacks provenance')
            saved = json.loads(record.read_text(encoding='utf-8'))
            if path.stat().st_size != size or digest_file(path) != saved['sha256']:
                raise ValueError('Downloaded archive changed')
            return saved
        part = raw / f'{name}.corpus.zip.partial'
        if part.exists():
            raise FileExistsError('Preserve failed partial download')
        digest = hashlib.sha256()
        count = 0
        with urlopen(url, timeout=120) as response, part.open('xb') as target:
            while block := response.read(4 * 1024**2):
                count += len(block)
                if count > size:
                    raise ValueError('Archive exceeds frozen catalogue size')
                if shutil.disk_usage(raw).free < minimum_free_gib * 2**30:
                    raise RuntimeError('Free disk limit reached')
                target.write(block)
                digest.update(block)
                if count // (64 * 1024**2) != (count-len(block)) // (64 * 1024**2):
                    print(f'download {name}: {count}/{size} bytes', flush=True)
        if count != size:
            raise ValueError('Incomplete or changed catalogue archive')
        with zipfile.ZipFile(part) as archive:
            if archive.testzip() is not None:
                raise ValueError('Confirmation ZIP CRC mismatch')
            utterance_member(archive)
        part.rename(path)
        result = dict(corpus=name, url=url, bytes=count,
                      sha256=digest.hexdigest(), crc='passed')
        with record.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
        print(f'download {name}: complete, hash and CRC recorded', flush=True)
        return result

    with ThreadPoolExecutor(max_workers=2) as executor:
        return list(executor.map(download, CORPORA))
