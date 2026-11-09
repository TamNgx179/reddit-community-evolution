"""Package verified frozen tables and replay evidence for collaborators."""

import argparse
from pathlib import Path

from reddit_sna.evaluation.artifact_acceptance import package_delivery, verify_bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        print(f"Verified {len(verify_bundle(args.verify)['sha256'])} bundle files")
    elif args.replay and args.output:
        print(package_delivery(args.repository, args.replay, args.output))
    else:
        parser.error("Provide --verify, or both --replay and --output")


if __name__ == "__main__":
    main()
