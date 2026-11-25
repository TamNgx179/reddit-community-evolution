#!/usr/bin/env python3
"""Run the frozen Anh evaluation protocol on a prediction CSV."""
from __future__ import annotations


import argparse
from pathlib import Path
import sys



ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from reddit_sna.evaluation.locked_metrics import write_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", required=True, help="CSV following the locked prediction contract")
    parser.add_argument("--output", required=True, help="New directory for evaluation CSVs; must not exist")
    args = parser.parse_args()
    tables = write_evaluation(args.predictions, args.output)
    print(f"Evaluation complete: {args.output}")
    for name, table in tables.items():
        print(f"{name}: {len(table)} rows")


if __name__ == "__main__":
    main()
