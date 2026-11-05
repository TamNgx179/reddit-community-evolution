"""Create a non-submitted AI-assisted reviewer-1 draft from two CSV files."""

import argparse
import json
from pathlib import Path

from reddit_sna.reporting.review_draft import (
    create_ai_assisted_draft,
    create_submission_ready_package,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    draft = commands.add_parser('draft', help='create a non-submitted AI-assisted draft')
    draft.add_argument('--blank-worksheet', type=Path, required=True)
    draft.add_argument('--automated-assessment', type=Path, required=True)
    draft.add_argument('--output', type=Path, required=True)
    draft.add_argument('--reviewer-id', required=True)
    draft.add_argument('--guidance-version', default='frozen_v1.1')
    finalize = commands.add_parser('finalize', help='create a coordinator-ready adopted package')
    finalize.add_argument('--draft-directory', type=Path, required=True)
    finalize.add_argument('--output', type=Path, required=True)
    finalize.add_argument('--reviewer-id', required=True)
    finalize.add_argument('--adoption-note', required=True)
    args = parser.parse_args(argv)
    if args.command == 'draft':
        result = create_ai_assisted_draft(
            args.blank_worksheet,
            args.automated_assessment,
            args.output,
            args.reviewer_id,
            guidance_version=args.guidance_version,
        )
    else:
        result = create_submission_ready_package(
            args.draft_directory,
            args.output,
            args.reviewer_id,
            args.adoption_note,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
