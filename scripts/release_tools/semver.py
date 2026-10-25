"""Strict Semantic Versioning 2.0.0 parsing and this project's bump arithmetic.

Reference: https://semver.org/spec/v2.0.0.html. The regular expression below is the one the
specification publishes in its FAQ ("Is there a suggested regular expression (RegEx) to check a
SemVer string?"), with named groups, so parsing matches the standard exactly rather than an
approximation of it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from release_tools.bump import Bump

# Official SemVer 2.0.0 regular expression (named-group variant from semver.org). It rejects
# leading zeros in numeric identifiers, empty identifiers, and anything outside [0-9A-Za-z-].
# re.ASCII is essential: without it Python's \d also matches non-ASCII digits such as "١".
# Callers use fullmatch() because "$" alone would also accept a trailing newline.
_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$",
    re.ASCII,
)

# Release tags are the SemVer string prefixed with a lowercase "v" (for example "v1.2.3"). The
# prefix is a widespread convention, not part of SemVer itself; SemVer's FAQ notes that "v1.2.3"
# is not a semantic version, which is why the prefix is stripped before parsing.
TAG_PREFIX = "v"


class SemverError(ValueError):
    """Raised when a string is not a valid SemVer 2.0.0 version."""


@dataclass(frozen=True, order=False)
class Version:
    """A parsed semantic version.

    Only final releases (no pre-release, no build metadata) are produced by the release tooling,
    but pre-release and build fields are parsed so that such tags can be recognised and reported
    instead of being mistaken for malformed input.
    """

    major: int
    minor: int
    patch: int
    prerelease: str | None = None
    buildmetadata: str | None = None

    @classmethod
    def parse(cls, text: str) -> "Version":
        """Parse ``text`` as a SemVer 2.0.0 string, raising ``SemverError`` on any deviation."""
        match = _SEMVER_RE.fullmatch(text)
        if match is None:
            raise SemverError(f"{text!r} is not a valid SemVer 2.0.0 version")
        return cls(
            major=int(match["major"]),
            minor=int(match["minor"]),
            patch=int(match["patch"]),
            prerelease=match["prerelease"],
            buildmetadata=match["buildmetadata"],
        )

    @classmethod
    def from_tag(cls, tag: str) -> "Version":
        """Parse a release tag such as ``v1.2.3``; the ``v`` prefix is mandatory."""
        if not tag.startswith(TAG_PREFIX):
            raise SemverError(f"tag {tag!r} does not start with {TAG_PREFIX!r}")
        return cls.parse(tag[len(TAG_PREFIX) :])

    @property
    def is_final(self) -> bool:
        """True for a plain ``MAJOR.MINOR.PATCH`` release without pre-release or build parts."""
        return self.prerelease is None and self.buildmetadata is None

    @property
    def tag(self) -> str:
        """The git tag name for this version."""
        return f"{TAG_PREFIX}{self}"

    def core(self) -> tuple[int, int, int]:
        """The numeric precedence key of a final release (build metadata never affects order)."""
        return (self.major, self.minor, self.patch)

    def bumped(self, bump: Bump) -> "Version":
        """Return the next final version after applying ``bump`` to this final version.

        SemVer item 4 states that major version zero is for initial development and that
        "anything MAY change at any time"; it does not prescribe how breaking changes map onto
        0.y.z. This project's documented policy (CONTRIBUTING.md, "Versioning") is:

        * ``1.0.0`` and later: breaking -> MAJOR, feature -> MINOR, fix -> PATCH (SemVer 8, 7, 6).
        * ``0.y.z``: breaking -> MINOR and feature -> MINOR, fix -> PATCH, so that leaving 0.x is
          always a deliberate decision rather than a side effect of a ``!`` in a commit header.
          The jump to 1.0.0 is made by preparing a ``## [1.0.0]`` changelog section explicitly.
        """
        if not self.is_final:
            raise SemverError(f"cannot bump non-final version {self}")
        if bump is Bump.NONE:
            raise SemverError("a release requires at least one change that bumps the version")
        if self.major == 0 and bump is Bump.MAJOR:
            bump = Bump.MINOR
        if bump is Bump.MAJOR:
            return Version(self.major + 1, 0, 0)
        if bump is Bump.MINOR:
            return Version(self.major, self.minor + 1, 0)
        return Version(self.major, self.minor, self.patch + 1)

    def __str__(self) -> str:
        text = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease is not None:
            text += f"-{self.prerelease}"
        if self.buildmetadata is not None:
            text += f"+{self.buildmetadata}"
        return text
