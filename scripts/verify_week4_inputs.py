"""Verify the selected frozen inputs for the Week 4 core acceptance."""

import argparse
from pathlib import Path

from reddit_sna.evaluation.artifact_acceptance import run_acceptance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--contract", type=Path, default=Path("configs/week4_acceptance.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_acceptance(args.repository, args.contract, args.output)
    print(f"Accepted {len(result['cohorts'])} cohorts; H1 {result['h1_dependency']['status']}")


if __name__ == "__main__":
    main()
