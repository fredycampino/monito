#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*))?$"
)
TAG_PATTERN = re.compile(r"^v(?P<version>.+)$")
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


def version_key(version: str) -> tuple[int, int, int, tuple[tuple[int, int | str], ...]]:
    match = SEMVER_PATTERN.fullmatch(version)
    if match is None:
        raise ValueError(f"invalid semantic version: {version}")

    major, minor, patch, prerelease = match.groups()
    if prerelease is None:
        prerelease_key = ((2, ""),)
    else:
        prerelease_key = tuple(
            (0, int(identifier)) if identifier.isdigit() else (1, identifier)
            for identifier in prerelease.split(".")
        )
    return int(major), int(minor), int(patch), prerelease_key


def published_versions() -> set[str]:
    completed = subprocess.run(
        ["git", "tag", "--list", "v*"],
        check=True,
        capture_output=True,
        text=True,
    )
    versions = set()
    for tag in completed.stdout.splitlines():
        match = TAG_PATTERN.fullmatch(tag)
        if match and SEMVER_PATTERN.fullmatch(match.group("version")):
            versions.add(match.group("version"))
    return versions


def validate_release_version(version: str) -> None:
    published = published_versions()
    if version in published:
        fail(f"release tag already exists: v{version}")
    if published:
        latest = max(published, key=version_key)
        if version_key(version) <= version_key(latest):
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
