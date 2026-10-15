"""Read-only ConvoKit archive inventory and integrity verification."""

import hashlib
import json
from pathlib import Path
import zipfile

CORPORA = (
    "Ask_Politics", "AskALiberal", "AskThe_Donald", "AskTrumpSupporters",
    "Conservative", "democrats", "EnoughTrumpSpam", "hillaryclinton",
    "moderatepolitics", "NeutralPolitics", "Political_Revolution",
    "PoliticalDiscussion", "Republican", "SandersForPresident", "socialism",
)


def digest_file(path: Path) -> str:
    """Compute streaming SHA-256 without loading a potentially large corpus into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def utterance_member(archive: zipfile.ZipFile) -> str:
    """Find the unique supported JSONL member; reject ambiguous archive layouts."""
    names = [item.filename for item in archive.infolist()
             if item.filename.split("/")[-1] == "utterances.jsonl"]
    if len(names) != 1:
        raise ValueError("archive must contain exactly one utterances.jsonl member")
    return names[0]


def selected_archives(root: Path, names: tuple[str, ...] = CORPORA) -> list[Path]:
    """Resolve an explicit corpus allowlist and require every requested ZIP to exist."""
    if not names or len(set(names)) != len(names):
        raise ValueError("corpus selection must be nonempty and unique")
    if any(name not in CORPORA for name in names):
        raise ValueError("unknown corpus in selection")
    paths = [root / f"{name}.corpus.zip" for name in sorted(names)]
    if any(not path.is_file() for path in paths):
        raise ValueError("declared corpus archive is missing")
    return paths


def audit_archives(paths: list[Path], progress=print) -> dict:
    """Audit SHA-256, every ZIP member CRC and a schema sample without extracting files.

    Return aggregate/archive metadata; schema sampling does not replace full normalization validation."""
    records = []
    for path in paths:
        before = path.stat()
        sha = digest_file(path)
        with zipfile.ZipFile(path) as archive:
            member = utterance_member(archive)
            # Read every member for CRC; no filesystem extraction.
            if archive.testzip() is not None:
                raise ValueError(f"CRC failure in {path.name}")
            with archive.open(member) as handle:
                try:
                    first = json.loads(next(handle))
                except (StopIteration, ValueError) as exc:
                    raise ValueError(f"empty/invalid utterance sample in {path.name}") from exc
            if not isinstance(first, dict):
                raise ValueError(f"invalid utterance sample in {path.name}")
            keys = set(first)
            if not {"id", "timestamp"}.issubset(keys) or not keys & {"root", "conversation_id"}:
                raise ValueError(f"unsupported utterance schema in {path.name}")
            records.append({"archive": path.name, "bytes": before.st_size,
                            "sha256": sha, "crc": "passed", "utterance_member": member,
                            "sample_field_names": sorted(keys),
                            "schema_check": "first_record_only; full normalization validates rows"})
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("input archive changed during audit")
        progress(f"audit: {path.name} checksum/CRC passed", flush=True)
    return {"status": "complete", "archives": records, "count": len(records)}
