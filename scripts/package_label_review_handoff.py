"""Create an isolated reviewer or coordinator handoff from a prepared packet."""

import argparse
import json
from pathlib import Path

from reddit_sna.reporting.label_review_handoff import package_label_review_handoff


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--role", choices=("reviewer_a", "reviewer_b", "coordinator"), required=True)
    args = parser.parse_args(argv)
    print(json.dumps(package_label_review_handoff(args.packet, args.output, args.role), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
