#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
TAG_PATTERN = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
PLACEHOLDER_LINES = {
    "- Nothing yet.",
    "- Update this section when a branch is ready for release.",
}


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--head-ref", required=True)
    return parser.parse_args()


def release_version(head_ref: str) -> str:
    prefix = "release/"
    if not head_ref.startswith(prefix):
        fail(f"release branch must start with {prefix}, got {head_ref}")
    version = head_ref.removeprefix(prefix)
    if not SEMVER_PATTERN.fullmatch(version):
        fail(f"release branch must end with a semantic version, got {version}")
    return version


def version_tuple(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def published_versions() -> set[tuple[int, int, int]]:
    completed = subprocess.run(
        ["git", "tag", "--list", "v*"],
        check=True,
        capture_output=True,
        text=True,
    )
    versions = set()
    for tag in completed.stdout.splitlines():
        match = TAG_PATTERN.fullmatch(tag)
        if match:
            versions.add(tuple(int(part) for part in match.groups()))
    return versions


def validate_release_version(version: str) -> None:
    proposed = version_tuple(version)
    published = published_versions()
    if proposed in published:
        fail(f"release tag already exists: v{version}")
    if published and proposed <= max(published):
        latest = ".".join(str(part) for part in max(published))
        fail(f"release version {version} must be greater than latest tag v{latest}")


def section(lines: list[str], heading: str) -> list[str]:
    try:
        start = lines.index(heading) + 1
    except ValueError:
        fail(f"CHANGELOG.md is missing section: {heading}")
    end = next(
        (index for index in range(start, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    return lines[start:end]


def entries(lines: list[str]) -> set[str]:
    return {line.strip() for line in lines if line.strip().startswith("- ")}


def main() -> None:
    version = release_version(parse_args().head_ref)
    validate_release_version(version)

    file_version = Path("VERSION").read_text(encoding="utf-8").strip()
    if file_version != version:
        fail(f"VERSION must match release branch version {version}, got {file_version}")

    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8").splitlines()
    unreleased_entries = entries(section(changelog, "## Unreleased")) - PLACEHOLDER_LINES
    if unreleased_entries:
        fail("CHANGELOG.md Unreleased must be empty for a release PR")

    version_heading = next(
        (line for line in changelog if line.startswith(f"## {version} - ")),
        None,
    )
    if version_heading is None:
        fail(f"CHANGELOG.md must contain a closed section for version {version}")
    if not entries(section(changelog, version_heading)) - PLACEHOLDER_LINES:
        fail(f"CHANGELOG.md version section {version} must contain release notes")

    print(f"validated release metadata for version {version}")


if __name__ == "__main__":
    main()
