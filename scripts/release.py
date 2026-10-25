#!/usr/bin/env python3
"""Plan and verify releases from git tags, Conventional Commits and CHANGELOG.md.

Subcommands:
  plan                 print the next version computed from the commits since the latest tag
  verify               plan, then check CHANGELOG.md is prepared for exactly that version
  notes --version X    write the CHANGELOG section of X to --output, for the GitHub Release body

``verify`` and ``notes`` are what ``.github/workflows/release.yml`` runs; ``plan`` is safe to run
anywhere. None of these commands create tags or publish anything: publishing only happens in the
release workflow (CLAUDE.md, "Verification policy").
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from release_tools.annotations import Reporter, write_github_outputs
from release_tools.changelog import Changelog, ChangelogError
from release_tools.git import Git, GitError
from release_tools.release_plan import PlanError, ReleasePlan, check_readiness, plan
from release_tools.repository import RepositoryUrlError, repository_url
from release_tools.semver import SemverError, Version

CHANGELOG = "CHANGELOG.md"


def _plan_summary(release: ReleasePlan) -> str:
    """Markdown explaining which commits produced which bump."""
    lines = [
        "### Release plan",
        "",
        f"* Previous release: `{release.previous_tag or 'none (first release)'}`",
        f"* Next version: `{release.next}` (bump: {release.bump.name.lower()})",
        f"* Release commit: `{release.head}`",
        "",
        "| Commit | Bump | Header |",
        "| --- | --- | --- |",
    ]
    for commit, bump in release.commits:
        header = commit.message.splitlines()[0].replace("|", "\\|").replace("`", "'")
        lines.append(f"| `{commit.short}` | {bump.name.lower()} | `{header}` |")
    if release.nonconforming:
        lines += ["", "Pre-release history that is not Conventional (tolerated before the first "
                      "release):", ""] + [f"* `{item}`" for item in release.nonconforming]
    if release.ignored_tags:
        lines += ["", "Ignored tags (not final `vX.Y.Z`): "
                  + ", ".join(f"`{t}`" for t in release.ignored_tags)]
    return "\n".join(lines)


def _cmd_plan(git: Git, reporter: Reporter, args: argparse.Namespace) -> int:
    release = plan(git, args.head)
    reporter.notice(f"next version {release.next} (previous: {release.previous_tag or 'none'})",
                    title="Release plan")
    reporter.summary(_plan_summary(release))
    write_github_outputs({"version": str(release.next), "tag": release.next.tag,
                          "previous_tag": release.previous_tag or "", "sha": release.head})
    print(release.next)
    return 0


def _cmd_verify(git: Git, reporter: Reporter, args: argparse.Namespace) -> int:
    release = plan(git, args.head)
    root = git.toplevel()
    changelog = Changelog.read(root / CHANGELOG)
    version, problems = check_readiness(release, changelog, git.tags(), repository_url(git))
    for problem in problems:
        reporter.error(problem.message, title="Release not ready", file=CHANGELOG,
                       line=problem.line)
    reporter.summary(_plan_summary(release))
    if version is None or problems:
        return 1
    reporter.notice(f"ready to release {version.tag} at {release.head}", title="Release verified")
    write_github_outputs({"version": str(version), "tag": version.tag,
                          "previous_tag": release.previous_tag or "", "sha": release.head})
    print(version)
    return 0


def _cmd_notes(git: Git, reporter: Reporter, args: argparse.Namespace) -> int:
    version = Version.parse(args.version)
    changelog = Changelog.read(git.toplevel() / CHANGELOG)
    section = changelog.find(version)
    if section is None:
        reporter.error(f"CHANGELOG.md has no [{version}] section", title="Release notes",
                       file=CHANGELOG)
        return 1
    url = changelog.expected_links(repository_url(git)).get(str(version))
    body = "\n".join(section.body).strip("\n")
    notes = f"{body}\n\n**Full changelog**: {url}\n" if url else f"{body}\n"
    args.output.write_text(notes, encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--head", default="HEAD", help="commit to release (default: HEAD)")
    notes = sub.add_parser("notes")
    notes.add_argument("--version", required=True)
    notes.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    reporter = Reporter()
    handlers = {"plan": _cmd_plan, "verify": _cmd_verify, "notes": _cmd_notes}
    try:
        return handlers[args.command](Git(Path.cwd()), reporter, args)
    except (PlanError, GitError, ChangelogError, RepositoryUrlError, SemverError) as exc:
        file = CHANGELOG if isinstance(exc, ChangelogError) else None
        line = exc.line if isinstance(exc, ChangelogError) else None
        reporter.error(str(exc), title=f"release {args.command} failed", file=file, line=line)
        return 1


if __name__ == "__main__":
    sys.exit(main())
