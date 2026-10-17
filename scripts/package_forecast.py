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
    docs = Path(__file__).resolve().parents[1] / "reports"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for relative in sorted(delivery["manifest"]["artifact_hashes"]):
            bundle.write(args.run / relative, relative)
        bundle.write(args.run / "manifest.json", "manifest.json")
        for name in ("FORECAST-HANDOFF.md", "FORECAST-GED-RESULTS.md"):
            if (docs / name).exists():
                bundle.write(docs / name, name)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
