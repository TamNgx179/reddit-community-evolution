"""Download the declared 15 Cornell corpora without loading ConvoKit in memory."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
from urllib.parse import unquote, urljoin
from urllib.request import Request, urlopen
import zipfile

from reddit_sna.data.archive import CORPORA, digest_file, utterance_member

BASE = "https://zissou.infosci.cornell.edu/convokit/datasets/subreddit-corpus/corpus-zipped/"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.extend(v for k, v in attrs if k == "href" and v)


def listing(url):
    parser = Links()
    with urlopen(url, timeout=60) as response:
        parser.feed(response.read().decode("utf-8"))
    return parser.links


def discover():
    directories = listing(BASE)
    selected = {}
    for name in CORPORA:
        matches = []
        for href in directories:
            interval = unquote(href).rstrip("/").split("~-~")
            if len(interval) == 2 and interval[0] <= name <= interval[1]:
                matches.append(urljoin(BASE, href))
        if len(matches) != 1:
            raise ValueError(f"Cannot resolve index directory for {name}")
        selected[name] = matches[0]
    pages = {url: listing(url) for url in sorted(set(selected.values()))}
    result = []
    for name, folder in selected.items():
        matches = [urljoin(folder, href) for href in pages[folder]
                   if unquote(href).split("/")[-1] == f"{name}.corpus.zip"]
        if len(matches) != 1:
            raise ValueError(f"Cannot resolve archive for {name}")
        with urlopen(Request(matches[0], method="HEAD"), timeout=60) as response:
            size = int(response.headers["Content-Length"])
        result.append(dict(corpus=name, url=matches[0], bytes=size))
    return result


def download(item, root):
    destination = root / f"{item['corpus']}.corpus.zip"
    if not destination.exists():
        partial = destination.with_suffix(".zip.part")
        if partial.exists():
            raise FileExistsError(f"Partial file requires inspection: {partial}")
        print(f"Downloading {item['corpus']} ({item['bytes'] / 1e6:.1f} MB)", flush=True)
        with urlopen(item["url"], timeout=120) as source, partial.open("xb") as target:
            shutil.copyfileobj(source, target, 1024 * 1024)
        if partial.stat().st_size != item["bytes"]:
            raise ValueError("Download size mismatch")
        partial.rename(destination)
    if destination.stat().st_size != item["bytes"]:
        raise ValueError(f"Existing archive size mismatch: {destination.name}")
    with zipfile.ZipFile(destination) as archive:
        utterance_member(archive)
        if archive.testzip() is not None:
            raise ValueError(f"CRC failure: {destination.name}")
    result = {**item, "sha256": digest_file(destination), "crc": "passed"}
    print(f"Verified {destination.name}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "data" / "raw"
    plan = discover()
    total = sum(item["bytes"] for item in plan)
    print(json.dumps({"archives": plan, "total_bytes": total}, indent=2), flush=True)
    if not args.download:
        return
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < total * 4:
        raise ValueError("Insufficient free space for downloads and processing")
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(lambda item: download(item, root), plan))
    (root / "download_manifest.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
