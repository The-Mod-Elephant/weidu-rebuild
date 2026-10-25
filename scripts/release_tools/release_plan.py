"""Computation of the next release version from git history, and release-readiness checks.

The version source is git tags (CLAUDE.md, "Sources of truth"): the newest final ``vX.Y.Z`` tag
reachable from the release commit is the current version, and the Conventional Commits made
since then decide the bump. The plan is pure data so the same logic serves the local
``scripts/release.py`` / ``scripts/changelog.py`` commands and ``.github/workflows/release.yml``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from release_tools import conventional
from release_tools.bump import Bump
from release_tools.changelog import Changelog
from release_tools.changelog_validation import validate
from release_tools.git import Commit, Git
from release_tools.problem import Problem
from release_tools.semver import SemverError, Version

# SemVer FAQ ("How should I deal with revisions in the 0.y.z initial development phase?"):
# "The simplest thing to do is start your initial development release at 0.1.0".
INITIAL_VERSION = Version(0, 1, 0)

# Leaving initial development is an explicit act (see Version.bumped): a prepared changelog
# section for exactly 1.0.0 is accepted in place of the computed 0.x version.
FIRST_STABLE = Version(1, 0, 0)


class PlanError(RuntimeError):
    """The release cannot be planned; the message explains what to fix."""


@dataclass
class ReleasePlan:
    """Everything known about the release that ``head`` would produce."""

    head: str
    previous: Version | None
    next: Version
    bump: Bump
    commits: list[tuple[Commit, Bump]] = field(default_factory=list)
    ignored_tags: list[str] = field(default_factory=list)
    # Non-conforming commits tolerated before the first release; reported, never silently dropped.
    nonconforming: list[str] = field(default_factory=list)

    @property
    def previous_tag(self) -> str | None:
        return self.previous.tag if self.previous else None


def _latest_final_tag(git: Git, head: str) -> tuple[Version | None, list[str]]:
    """Newest final release tag reachable from ``head``, plus tags that were not understood."""
    latest: Version | None = None
    ignored: list[str] = []
    for tag in git.tags_merged_into(head):
        try:
            version = Version.from_tag(tag)
        except SemverError:
            ignored.append(tag)
            continue
        if not version.is_final:
            ignored.append(tag)
            continue
        if latest is None or version.core() > latest.core():
            latest = version
    return latest, ignored


def plan(git: Git, head: str = "HEAD") -> ReleasePlan:
    """Plan the release of ``head``; raises ``PlanError`` with an actionable message."""
    if git.is_shallow():
        raise PlanError("the repository is a shallow clone, so tags and commit history are "
                        "incomplete; fetch full history (actions/checkout `fetch-depth: 0`)")
    head_sha = git.resolve(head)
    previous, ignored = _latest_final_tag(git, head_sha)
    rev_range = f"{previous.tag}..{head_sha}" if previous else head_sha

    classified: list[tuple[Commit, Bump]] = []
    invalid: list[str] = []
    for commit in git.commits(rev_range):
        if commit.is_merge:
            continue  # main has linear history; merges can only appear in local experiments
        result = conventional.parse(commit.message)
        if not result.ok or result.commit is None:
            reasons = "; ".join(p.message for p in result.problems) or "unparsable header"
            invalid.append(f"{commit.short} {commit.message.splitlines()[0] if commit.message else ''}"
                           f" -> {reasons}")
            continue
        classified.append((commit, result.commit.bump))

    if invalid and previous is not None:
        # Before the first release, history predates commit linting, so non-conforming commits
        # are tolerated; afterwards every commit on main has passed the linter, so a bad one means
        # something bypassed it and the computed version cannot be trusted.
        raise PlanError("commits since the last release are not Conventional Commits:\n  "
                        + "\n  ".join(invalid))

    bump = max((b for _, b in classified), default=Bump.NONE)
    if previous is None:
        return ReleasePlan(head_sha, None, INITIAL_VERSION, max(bump, Bump.MINOR), classified,
                           ignored, invalid)
    if bump is Bump.NONE:
        raise PlanError(f"no commit since {previous.tag} requires a release (only types that "
                        "bump nothing, such as docs/ci/chore, were found)")
    return ReleasePlan(head_sha, previous, previous.bumped(bump), bump, classified, ignored)


def check_readiness(release: ReleasePlan, changelog: Changelog, all_tags: list[str],
                    repo_url: str) -> tuple[Version | None, list[Problem]]:
    """Verify the changelog is prepared for ``release``; returns the version to tag and problems.

    The version to tag is normally ``release.next``; it is ``1.0.0`` when that section was
    prepared deliberately while still in 0.x.
    """
    problems = list(validate(changelog, repo_url, all_tags))
    unreleased = changelog.unreleased
    if unreleased is not None and unreleased.has_entries():
        problems.append(Problem(unreleased.line, "the Unreleased section still has entries; run "
                                                 "`python3 scripts/changelog.py prepare` in a PR "
                                                 "first"))
    released = changelog.released()
    if not released:
        problems.append(Problem(1, f"no '## [{release.next}]' section was prepared"))
        return None, problems
    top = released[0]
    try:
        top_version = top.version
    except SemverError as exc:
        problems.append(Problem(top.line, str(exc)))
        return None, problems

    graduating = (top_version == FIRST_STABLE
                  and (release.previous is None or release.previous.major == 0))
    if top_version != release.next and not graduating and top_version.tag in all_tags:
        problems.append(Problem(top.line, f"no '## [{release.next}]' section has been prepared "
                                          f"(the newest section [{top_version}] is already "
                                          "released); run `python3 scripts/changelog.py prepare`"
                                          " in a pull request first"))
        return None, problems
    if top_version != release.next and not graduating:
        problems.append(Problem(top.line, f"the newest section is [{top_version}] but the commits "
                                          f"since {release.previous_tag or 'the start'} require "
                                          f"[{release.next}]"))
        return None, problems
    if top_version.tag in all_tags:
        problems.append(Problem(top.line, f"tag {top_version.tag} already exists"))
        return None, problems
    return top_version, problems
