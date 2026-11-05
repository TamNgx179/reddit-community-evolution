"""Check a reviewer-1 ZIP and create a separate blank working copy."""

import argparse
import json
from pathlib import Path

from reddit_sna.reporting.review_intake import prepare_reviewer_workspace


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', dest='archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--phase', choices=('pilot', 'main'), required=True)
    parser.add_argument('--reviewer-id', required=True)
    parser.add_argument('--expected-sha256')
    args = parser.parse_args(argv)
    result = prepare_reviewer_workspace(args.archive, args.output, args.phase,
        args.reviewer_id, expected_sha256=args.expected_sha256)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
