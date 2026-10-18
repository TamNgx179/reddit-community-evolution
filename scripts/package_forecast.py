"""Package a verified forecast handoff for offline use; no external upload."""

import argparse
from pathlib import Path
import zipfile

from reddit_sna.reporting.forecast_handoff import read_handoff


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    delivery = read_handoff(args.run)
    project = Path(__file__).resolve().parents[1]
    # Preserve the six-document layout so relative navigation also works offline.
    documents = (
        "README.md", "PHAN-CONG-SNA-8-TUAN.md", "docs/METHODS.md",
        "docs/RUNBOOK.md", "docs/RESULTS.md", "docs/LABEL_REVIEW.md",
    )
    for relative in documents:
        if not (project / relative).is_file():
            raise FileNotFoundError(f"Missing handoff document: {relative}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for relative in sorted(delivery["manifest"]["artifact_hashes"]):
            bundle.write(args.run / relative, relative)
        bundle.write(args.run / "manifest.json", "manifest.json")
        for relative in documents:
            bundle.write(project / relative, relative)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
