#!/usr/bin/env python3
"""Validate commit messages (and a pull request title) against Conventional Commits 1.0.0.

Usage:
  check_commits.py --base <rev> --head <rev> [--title "<PR title>"]   # every commit in base..head
  check_commits.py --message-file <path>                               # one message (commit-msg hook)

Every problem is reported as a GitHub annotation in CI (or "file:line: error:" locally) and a
Markdown table of the results is added to the job summary. The pull request title is checked
too because squash merges use it as the commit header that lands on ``main``.

The rules themselves live in ``release_tools.conventional`` and the allowed types in
``release_tools.commit_types``. Dependabot pull requests are exempted by the calling workflow.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from release_tools import conventional
from release_tools.annotations import Reporter
from release_tools.git import Git, GitError


def _check(reporter: Reporter, label: str, message: str, file: str | None) -> bool:
    """Validate one message, reporting every problem under ``label``; returns success."""
    result = conventional.parse(message)
    for problem in result.problems:
        reporter.error(problem.message, title=f"{label}: not a Conventional Commit", file=file,
                       line=problem.line if file else None)
    return result.ok


def _row(label: str, header: str, status: bool | str) -> str:
    """One summary-table row; ``status`` is pass/fail or a short explanatory word."""
    # Pipes would break the Markdown table, and backticks would unbalance inline code.
    safe = header.replace("|", "\\|").replace("`", "'")
    shown = status if isinstance(status, str) else ("✅ pass" if status else "❌ fail")
    return f"| {label} | {shown} | `{safe}` |"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="exclusive start of the commit range")
    parser.add_argument("--head", help="inclusive end of the commit range")
    parser.add_argument("--title", help="pull request title to validate as a commit header")
    parser.add_argument("--message-file", type=Path, help="validate a single message file")
    args = parser.parse_args(argv)
    reporter = Reporter()

    if args.message_file is not None:
        message = args.message_file.read_text(encoding="utf-8")
        _check(reporter, "commit message", message, str(args.message_file))
        return reporter.exit_code

    if not (args.base and args.head) and args.title is None:
        parser.error("pass --base and --head, --title, or --message-file")

    rows: list[str] = []
    if args.title is not None:
        rows.append(_row("PR title", args.title, _check(reporter, "PR title", args.title, None)))

    if args.base and args.head:
        try:
            commits = Git(Path.cwd()).commits(f"{args.base}..{args.head}")
        except GitError as exc:
            reporter.error(str(exc), title="Could not list the pull request commits")
            return reporter.exit_code
        for commit in commits:
            header = commit.message.splitlines()[0] if commit.message else ""
            if commit.is_merge:
                rows.append(_row(commit.short, header, "skipped (merge commit)"))
                continue
            rows.append(_row(commit.short, header, _check(reporter, f"Commit {commit.short}",
                                                          commit.message, None)))

    verdict = ("All messages follow Conventional Commits." if reporter.exit_code == 0 else
               f"{reporter.errors} problem(s) found. See CONTRIBUTING.md#commit-messages; fix "
               "commits with `git rebase -i` (reword) and the title by editing the pull request.")
    reporter.summary("\n".join(["### Conventional Commits", "", "| Item | Result | Header |",
                                "| --- | --- | --- |", *rows, "", verdict]))
    return reporter.exit_code


if __name__ == "__main__":
    sys.exit(main())
