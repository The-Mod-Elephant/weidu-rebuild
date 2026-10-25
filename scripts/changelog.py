#!/usr/bin/env python3
"""Validate and maintain CHANGELOG.md (Keep a Changelog 1.1.0).

Subcommands:
  validate                       check structure, ordering, links and tag consistency (CI runs this)
  prepare [--version X] [--date YYYY-MM-DD]
                                 promote [Unreleased] to a new release section; the version
                                 defaults to the one computed by `release.py plan`
  fix-links                      rewrite the link definitions from the release headings

``prepare`` only edits the file. Commit the result in a normal pull request
(``docs(changelog): prepare vX.Y.Z``); after it merges, run the release workflow.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from release_tools.annotations import Reporter
from release_tools.changelog import Changelog, ChangelogError
from release_tools.changelog_validation import validate
from release_tools.git import Git, GitError
from release_tools.release_plan import PlanError, plan
from release_tools.repository import RepositoryUrlError, repository_url
from release_tools.semver import SemverError, Version

CHANGELOG = "CHANGELOG.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--version", help="override the computed version (e.g. 1.0.0)")
    prepare.add_argument("--date", help="release date; defaults to today's date in UTC")
    sub.add_parser("fix-links")
    args = parser.parse_args(argv)

    reporter = Reporter()
    git = Git(Path.cwd())
    try:
        path = git.toplevel() / CHANGELOG
        changelog = Changelog.read(path)
        repo_url = repository_url(git)
        if args.command == "validate":
            for problem in validate(changelog, repo_url, git.tags()):
                reporter.error(problem.message, title="CHANGELOG.md", file=CHANGELOG,
                               line=problem.line)
            return reporter.exit_code
        if args.command == "prepare":
            version = Version.parse(args.version) if args.version else plan(git).next
            date = args.date or dt.datetime.now(dt.timezone.utc).date().isoformat()
            dt.date.fromisoformat(date)  # rejects impossible dates with a clear ValueError
            changelog.prepare(version, date, repo_url)
        else:
            changelog.links = {k: (v, 0) for k, v in changelog.expected_links(repo_url).items()}
        path.write_text(changelog.render(), encoding="utf-8")
        print(f"updated {CHANGELOG}")
        return 0
    except (ChangelogError, GitError, PlanError, RepositoryUrlError, SemverError, ValueError) as exc:
        line = exc.line if isinstance(exc, ChangelogError) else None
        reporter.error(str(exc), title=f"changelog {args.command} failed", file=CHANGELOG,
                       line=line)
        return 1


if __name__ == "__main__":
    sys.exit(main())
