#!/usr/bin/env python3
"""Decide which CI job groups a change needs, so unaffected jobs are skipped to save CI minutes.

Usage: detect_changes.py --base <rev> --head <rev>

Writes one ``<group>=true|false`` step output per group (see ``GROUPS``) and a summary table.
This replaces workflow-level ``paths:`` filters on purpose: a workflow skipped by ``paths`` never
reports its required status checks, which leaves pull requests blocked forever, whereas a job
skipped through an ``if:`` condition reports success to the ruleset.

Safety rules: when the base revision is unknown (new branch, force push, all-zero SHA) or the
CI definition or this classifier changed, every group runs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from release_tools.annotations import Reporter, write_github_outputs
from release_tools.git import Git, GitError

# group -> (exact paths, directory prefixes). Prefixes end with "/" so "crates/" never matches a
# hypothetical "crates-old/" directory.
GROUPS: dict[str, tuple[frozenset[str], tuple[str, ...]]] = {
    "rust": (
        frozenset({"Cargo.toml", "Cargo.lock", "rust-toolchain.toml", "deny.toml", "about.toml",
                   "about.hbs", "clippy.toml", "rustfmt.toml", ".cargo/config.toml"}),
        ("crates/",),
    ),
    "python": (
        # CHANGELOG.md and .gitmessage are validated by the Python tooling and its tests.
        frozenset({"CHANGELOG.md", ".gitmessage"}),
        ("scripts/",),
    ),
    "workflows": (
        frozenset({".github/dependabot.yml", "zizmor.yml", ".github/zizmor.yml"}),
        (".github/workflows/", ".github/actions/"),
    ),
}

# Changing any of these can alter what CI does for every group, so everything must run.
RUN_EVERYTHING = frozenset({".github/workflows/ci.yml", "scripts/detect_changes.py"})

_NULL_SHA = "0" * 40


def classify(paths: list[str]) -> dict[str, bool]:
    """Map each group to whether any of ``paths`` belongs to it."""
    if any(path in RUN_EVERYTHING for path in paths):
        return {group: True for group in GROUPS}
    return {
        group: any(path in exact or path.startswith(prefixes) for path in paths)
        for group, (exact, prefixes) in GROUPS.items()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="", help="base revision (empty or all-zero = unknown)")
    parser.add_argument("--head", required=True, help="head revision")
    args = parser.parse_args(argv)
    reporter = Reporter()

    reason: str
    if not args.base or args.base == _NULL_SHA:
        result = {group: True for group in GROUPS}
        reason = "base revision unknown; running every group"
    else:
        try:
            paths = Git(Path.cwd()).changed_files(args.base, args.head)
        except GitError as exc:
            # Fail open: running too much costs minutes, skipping a needed check costs correctness.
            reporter.warning(f"{exc}; running every group", title="Change detection fell back")
            paths = []
            result = {group: True for group in GROUPS}
            reason = "git diff failed; running every group"
        else:
            result = classify(paths)
            reason = f"{len(paths)} changed file(s)"

    write_github_outputs({group: "true" if run else "false" for group, run in result.items()})
    rows = [f"| {group} | {'run' if run else 'skip'} |" for group, run in result.items()]
    reporter.summary("\n".join(["### Change detection", "", reason, "", "| Group | Decision |",
                                "| --- | --- |", *rows]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
