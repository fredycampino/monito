#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PLACEHOLDER_LINES = {
    "- Nothing yet.",
    "- Update this section when a branch is ready for release.",
}


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--expected-base", required=True)
    return parser.parse_args()


def changelog_entries(changelog: str, *, missing_is_empty: bool = False) -> set[str]:
    lines = changelog.splitlines()
    try:
        start = lines.index("## Unreleased") + 1
    except ValueError:
        if missing_is_empty:
            return set()
        fail("CHANGELOG.md is missing the Unreleased section")

    end = next(
        (index for index in range(start, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    return {
        line.strip()
        for line in lines[start:end]
        if line.strip().startswith("- ") and line.strip() not in PLACEHOLDER_LINES
    }


def base_changelog(base_ref: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"origin/{base_ref}:CHANGELOG.md"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def main() -> None:
    args = parse_args()
    if args.base_ref != args.expected_base:
        fail(
            f"pull request base branch must be {args.expected_base}, got {args.base_ref}"
        )

    current_entries = changelog_entries(Path("CHANGELOG.md").read_text(encoding="utf-8"))
    inherited_entries = changelog_entries(
        base_changelog(args.expected_base), missing_is_empty=True
    )
    added_entries = current_entries - inherited_entries
    if not added_entries:
        fail("CHANGELOG.md Unreleased must add at least one meaningful entry")

    print("validated new feature changelog entry")


if __name__ == "__main__":
    main()
