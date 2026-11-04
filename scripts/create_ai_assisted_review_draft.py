"""Create a non-submitted AI-assisted reviewer-1 draft from two CSV files."""

import argparse
import json
from pathlib import Path

from reddit_sna.reporting.review_draft import create_ai_assisted_draft


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blank-worksheet', type=Path, required=True)
    parser.add_argument('--automated-assessment', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reviewer-id', required=True)
    parser.add_argument('--guidance-version', default='frozen_v1.1')
    args = parser.parse_args(argv)
    result = create_ai_assisted_draft(
        args.blank_worksheet,
        args.automated_assessment,
        args.output,
        args.reviewer_id,
        guidance_version=args.guidance_version,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
