"""Replay both fixed tracking splits on the original T02 handoff; create a new pair run."""
import argparse
import json
from pathlib import Path
import re

from reddit_sna.reporting.tracking_outputs import INPUT_PINS, SOURCE_RUNS, run_split


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/detection-tracking"))
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", args.run_id):
        parser.error("run-id must be one portable directory name")
    pair = (args.output_root / args.run_id).resolve()
    bundle = args.handoff.resolve()
    if pair.exists() or pair.is_relative_to(bundle) or bundle.is_relative_to(pair):
        parser.error("choose a new output separate from the handoff")
    outputs = {split: str(run_split(bundle, pair, run_id=split, split=split, source_run=SOURCE_RUNS[split],
                                   input_manifest_sha256=pin)) for split, pin in INPUT_PINS.items()}
    with (pair / "tracking-index.json").open("x", encoding="utf-8") as stream:
        json.dump({"status": "complete", "runs": {s: s for s in outputs}, "input_pins": INPUT_PINS,
                   "scope": "Fixed PR12 tracker replay; no historical Dang freeze certification"}, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": "complete", "runs": outputs}))


if __name__ == "__main__":
    main()
