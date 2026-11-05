"""Export Phuc's coverage handoff from a supplied frozen sample run."""

import argparse
import json
from pathlib import Path

from reddit_sna.evaluation.coverage_audit import run_coverage_audit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--terminal-month', required=True,
                        help='Last observed snapshot declared by the frozen handoff')
    parser.add_argument('--manifest-name', choices=('complete.json', 'manifest.json'), default='complete.json')
    parser.add_argument('--graph-index', type=Path,
                        help='JSON object mapping each YYYY-MM to its sealed monthly preparation directory')
    args = parser.parse_args(argv)
    directories = None
    if args.graph_index:
        index = args.graph_index.resolve()
        raw = json.loads(index.read_text(encoding='utf-8'))
        if not isinstance(raw, dict) or any(not isinstance(p, str) for p in raw.values()):
            parser.error('Graph index must map months to directory strings')
        directories = {m: (index.parent/p).resolve() for m, p in raw.items()}
    result = run_coverage_audit(args.sample_run, args.output, args.terminal_month,
        manifest_name=args.manifest_name, month_directories=directories)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
