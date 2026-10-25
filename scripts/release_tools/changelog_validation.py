"""Validation rules for ``CHANGELOG.md`` (Keep a Changelog 1.1.0 plus SemVer 2.0.0).

Each rule reports a ``Problem`` with the offending line so CI can annotate the exact place in the
file. The rules encode the format's guiding principles ("latest version comes first", "the
release date of each version is displayed", "keep an Unreleased section at the top") and the
repository's tag-based versioning: every final ``v*`` tag must have a section and every section
must have a tag, except for at most one prepared, not-yet-tagged release at the top.
"""

from __future__ import annotations

import datetime as dt
import re

from release_tools.changelog import CHANGE_TYPES, Changelog, Release
from release_tools.problem import Problem
from release_tools.semver import SemverError, Version

_SUBSECTION_RE = re.compile(r"^### (?P<name>.+?)\s*$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$", re.ASCII)


def _check_header(changelog: Changelog) -> list[Problem]:
    first = next((line for line in changelog.preamble if line.strip()), "")
    if first != "# Changelog":
        return [Problem(1, "the file must start with the heading '# Changelog'")]
    return []


def _check_body(release: Release) -> list[Problem]:
    """Only the six Keep a Changelog types may be used as subsections, each at most once."""
    problems: list[Problem] = []
    seen: set[str] = set()
    for offset, line in enumerate(release.body, start=1):
        match = _SUBSECTION_RE.match(line)
        if not match:
            continue
        name = match["name"]
        number = release.line + offset
        if name not in CHANGE_TYPES:
            problems.append(Problem(number, f"unknown change type '### {name}'; use one of: "
                                            + ", ".join(CHANGE_TYPES)))
        elif name in seen:
            problems.append(Problem(number, f"'### {name}' appears twice in [{release.name}]"))
        seen.add(name)
    return problems


def _check_released(release: Release) -> tuple[list[Problem], Version | None, dt.date | None]:
    problems: list[Problem] = []
    version: Version | None = None
    date: dt.date | None = None
    try:
        version = release.version
        if not version.is_final:
            problems.append(Problem(release.line, f"[{release.name}] must be a final release "
                                                  "version without pre-release or build metadata"))
    except SemverError as exc:
        problems.append(Problem(release.line, str(exc)))
    if release.date is None or not _ISO_DATE_RE.match(release.date):
        problems.append(Problem(release.line, f"[{release.name}] needs an ISO 8601 date: "
                                              f"'## [{release.name}] - YYYY-MM-DD'"))
    else:
        try:
            date = dt.date.fromisoformat(release.date)
        except ValueError:
            problems.append(Problem(release.line, f"{release.date} is not a real calendar date"))
    if not release.has_entries():
        problems.append(Problem(release.line, f"[{release.name}] has no entries"))
    return problems, version, date


def validate(changelog: Changelog, repo_url: str, tags: list[str] | None = None) -> list[Problem]:
    """Return every problem in ``changelog``; ``tags`` enables the tag-consistency rules."""
    problems = _check_header(changelog)

    unreleased = [r for r in changelog.releases if r.is_unreleased]
    if len(unreleased) != 1:
        problems.append(Problem(1, "there must be exactly one '## [Unreleased]' section"))
    elif changelog.releases[0] is not unreleased[0]:
        problems.append(Problem(unreleased[0].line, "'## [Unreleased]' must be the first section"))
    elif unreleased[0].date is not None or unreleased[0].yanked:
        problems.append(Problem(unreleased[0].line, "'## [Unreleased]' takes no date or marker"))

    previous: tuple[Version, dt.date, Release] | None = None
    seen: set[Version] = set()
    for release in changelog.releases:
        problems.extend(_check_body(release))
        if release.is_unreleased:
            continue
        found, version, date = _check_released(release)
        problems.extend(found)
        if version is None:
            continue
        if version in seen:
            problems.append(Problem(release.line, f"version {version} is listed more than once"))
        seen.add(version)
        if previous is not None and date is not None:
            prev_version, prev_date, _ = previous
            if version.core() >= prev_version.core():
                problems.append(Problem(release.line, f"{version} must be lower than the newer "
                                                      f"section above it ({prev_version})"))
            if date > prev_date:
                problems.append(Problem(release.line, f"{version} is dated after the newer "
                                                      f"release {prev_version}"))
        if date is not None:
            previous = (version, date, release)

    if not problems:
        problems.extend(_check_links(changelog, repo_url))
    if tags is not None and not problems:
        problems.extend(_check_tags(changelog, tags))
    return problems


def _check_links(changelog: Changelog, repo_url: str) -> list[Problem]:
    """Link definitions must equal the canonical set generated from the headings."""
    problems: list[Problem] = []
    expected = changelog.expected_links(repo_url)
    actual = {label: url for label, (url, _) in changelog.links.items()}
    last_line = max((line for _, line in changelog.links.values()), default=1)
    for label, url in expected.items():
        if actual.get(label) != url:
            line = changelog.links.get(label, ("", last_line))[1]
            problems.append(Problem(line, f"[{label}] must link to {url} (run "
                                          "`python3 scripts/changelog.py fix-links`)"))
    for label, (_, line) in changelog.links.items():
        if label not in expected:
            problems.append(Problem(line, f"[{label}] does not correspond to any section"))
    return problems


def _check_tags(changelog: Changelog, tags: list[str]) -> list[Problem]:
    """Sections and final release tags must correspond one to one (see module docstring)."""
    problems: list[Problem] = []
    tagged: set[Version] = set()
    for tag in tags:
        try:
            version = Version.from_tag(tag)
        except SemverError:
            continue
        if version.is_final:
            tagged.add(version)
    released = changelog.released()
    for index, release in enumerate(released):
        version = release.version
        if version in tagged:
            continue
        # Only the newest section may be "prepared but not yet tagged".
        if index != 0:
            problems.append(Problem(release.line, f"[{version}] has no matching tag v{version}"))
    listed = {release.version for release in released}
    for version in sorted(tagged - listed, key=Version.core):
        problems.append(Problem(1, f"tag v{version} has no '## [{version}]' section"))
    return problems
