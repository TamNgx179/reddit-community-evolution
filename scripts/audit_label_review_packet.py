"""Verify a blinded review-label packet without revealing the tracker key."""

import argparse
import json
from pathlib import Path

from reddit_sna.reporting.label_review_audit import audit_label_review_packet


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(audit_label_review_packet(args.packet, args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
