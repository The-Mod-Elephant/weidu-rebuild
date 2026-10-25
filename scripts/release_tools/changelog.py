"""A structural model of ``CHANGELOG.md`` in the Keep a Changelog 1.1.0 format.

Format reference: https://keepachangelog.com/en/1.1.0/. The model keeps each release's body
verbatim so that rendering a parsed file reproduces it, and regenerates the link reference
definitions at the bottom from the release list so they can never drift from the headings.
Validation rules live separately in ``release_tools.changelog_validation``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from release_tools.semver import SemverError, Version

UNRELEASED = "Unreleased"

# The six change types defined by Keep a Changelog 1.1.0 ("Types of changes"), in its order.
CHANGE_TYPES = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")

# "## [Unreleased]" or "## [1.2.3] - 2024-01-31", optionally suffixed by " [YANKED]" (the
# format's notation for pulled releases).
_RELEASE_RE = re.compile(
    r"^## \[(?P<name>[^\]]+)\](?: - (?P<date>\S+))?(?P<yanked> \[YANKED\])?\s*$"
)
# Markdown link reference definition: "[label]: url".
_LINK_RE = re.compile(r"^\[(?P<label>[^\]]+)\]:\s+(?P<url>\S+)\s*$")


class ChangelogError(ValueError):
    """The changelog cannot be parsed or transformed; carries a 1-based line number."""

    def __init__(self, line: int, message: str) -> None:
        super().__init__(f"line {line}: {message}")
        self.line = line
        self.message = message


@dataclass
class Release:
    """One ``## [...]`` section: its heading data and its body lines (without the heading)."""

    name: str
    date: str | None
    yanked: bool
    line: int
    body: list[str] = field(default_factory=list)

    @property
    def is_unreleased(self) -> bool:
        return self.name == UNRELEASED

    @property
    def version(self) -> Version:
        """The parsed version of a released section (raises for Unreleased or bad versions)."""
        return Version.parse(self.name)

    def has_entries(self) -> bool:
        """True when the body contains at least one list item."""
        return any(line.lstrip().startswith(("- ", "* ")) for line in self.body)

    def heading(self) -> str:
        text = f"## [{self.name}]"
        if self.date is not None:
            text += f" - {self.date}"
        if self.yanked:
            text += " [YANKED]"
        return text


@dataclass
class Changelog:
    """The whole document: free-form preamble, ordered releases, and link definitions."""

    preamble: list[str]
    releases: list[Release]
    links: dict[str, tuple[str, int]]

    @classmethod
    def parse(cls, text: str) -> "Changelog":
        preamble: list[str] = []
        releases: list[Release] = []
        links: dict[str, tuple[str, int]] = {}
        for number, line in enumerate(text.splitlines(), start=1):
            link = _LINK_RE.match(line)
            if link:
                label = link["label"]
                if label.lower() in {key.lower() for key in links}:
                    raise ChangelogError(number, f"duplicate link definition for [{label}]")
                links[label] = (link["url"], number)
                continue
            if line.startswith("## "):
                heading = _RELEASE_RE.match(line)
                if heading is None:
                    raise ChangelogError(number, "release headings must be '## [Unreleased]' or "
                                                 "'## [X.Y.Z] - YYYY-MM-DD'")
                releases.append(Release(heading["name"], heading["date"],
                                        heading["yanked"] is not None, number))
                continue
            if links and line.strip():
                raise ChangelogError(number, "link definitions must be the last lines of the file")
            (releases[-1].body if releases else preamble).append(line)
        return cls(preamble, releases, links)

    @classmethod
    def read(cls, path: Path) -> "Changelog":
        return cls.parse(path.read_text(encoding="utf-8"))

    @property
    def unreleased(self) -> Release | None:
        return next((r for r in self.releases if r.is_unreleased), None)

    def released(self) -> list[Release]:
        """Released sections in document order (newest first in a valid file)."""
        return [r for r in self.releases if not r.is_unreleased]

    def find(self, version: Version) -> Release | None:
        for release in self.released():
            try:
                if release.version == version:
                    return release
            except SemverError:
                continue
        return None

    def expected_links(self, repo_url: str) -> dict[str, str]:
        """Canonical link definitions derived from the release headings.

        Unreleased compares the newest tag with HEAD; each release compares with its predecessor;
        the oldest release links to its tag. With no release yet, Unreleased links to the commit
        history of HEAD.
        """
        versions = [r.name for r in self.released()]
        result: dict[str, str] = {}
        if self.unreleased is not None:
            result[UNRELEASED] = (f"{repo_url}/compare/v{versions[0]}...HEAD" if versions
                                  else f"{repo_url}/commits/HEAD")
        for index, name in enumerate(versions):
            if index + 1 < len(versions):
                result[name] = f"{repo_url}/compare/v{versions[index + 1]}...v{name}"
            else:
                result[name] = f"{repo_url}/releases/tag/v{name}"
        return result

    def prepare(self, version: Version, date: str, repo_url: str) -> None:
        """Promote the Unreleased entries into a new ``## [version] - date`` section."""
        unreleased = self.unreleased
        if unreleased is None:
            raise ChangelogError(1, "there is no '## [Unreleased]' section to promote")
        if not unreleased.has_entries():
            raise ChangelogError(unreleased.line, "the Unreleased section has no entries to release")
        if self.find(version) is not None:
            raise ChangelogError(self.find(version).line, f"version {version} already exists")
        index = self.releases.index(unreleased)
        body = _trim_blank(unreleased.body)
        self.releases.insert(index + 1, Release(str(version), date, False, unreleased.line, body))
        unreleased.body = []
        self.links = {k: (v, 0) for k, v in self.expected_links(repo_url).items()}

    def render(self) -> str:
        """Serialise the document with exactly one blank line between blocks."""
        blocks = ["\n".join(_trim_blank(self.preamble))]
        for release in self.releases:
            body = _trim_blank(release.body)
            blocks.append("\n".join([release.heading(), "", *body]) if body else release.heading())
        if self.links:
            blocks.append("\n".join(f"[{label}]: {url}" for label, (url, _) in self.links.items()))
        return "\n\n".join(block for block in blocks if block) + "\n"


def _trim_blank(lines: list[str]) -> list[str]:
    """Strip leading and trailing blank lines, keeping interior spacing untouched."""
    start, end = 0, len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]
