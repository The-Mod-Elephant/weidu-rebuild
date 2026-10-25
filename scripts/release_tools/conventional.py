"""Parsing and validation of commit messages against Conventional Commits 1.0.0.

Specification: https://www.conventionalcommits.org/en/v1.0.0/. Numbered references in comments
("spec 1", "spec 13" ...) point at the items of the specification's "Specification" section.

Beyond the specification, this repository applies two documented house rules (CLAUDE.md,
CONTRIBUTING.md): the type must be one of ``COMMIT_TYPES`` and the header line may be at most
``MAX_HEADER_LENGTH`` characters long.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from release_tools.bump import Bump
from release_tools.commit_types import COMMIT_TYPES
from release_tools.problem import Problem

MAX_HEADER_LENGTH = 100

# Header grammar: <type>[(<scope>)][!]: <description>   (spec 1, 4, 5, 13)
# * The type is a noun; this repository restricts it to lowercase ASCII letters and then checks
#   it against COMMIT_TYPES, so the regex only has to recognise the overall shape.
# * The scope is "a noun describing a section of the codebase surrounded by parenthesis" (spec 4);
#   it is restricted here to lowercase kebab-case path-like words so scopes stay greppable.
# * Exactly one space must follow the colon (spec 5: "a colon and a space").
_HEADER_RE = re.compile(
    r"^(?P<type>[A-Za-z]+)"
    r"(?:\((?P<scope>[^()\r\n]*)\))?"
    r"(?P<breaking>!)?"
    r": (?P<description>.*)$",
    re.ASCII,
)
_SCOPE_RE = re.compile(r"^[a-z0-9]+(?:[-_/.][a-z0-9]+)*$", re.ASCII)

# Footer tokens (spec 8-10): a word token using "-" instead of spaces, followed by ": " or " #".
# "BREAKING CHANGE" is the one token allowed to contain a space (spec 9, 12) and "BREAKING-CHANGE"
# is its synonym (spec 16); both must be uppercase (spec 15).
_FOOTER_RE = re.compile(r"^(?P<token>BREAKING CHANGE|[A-Za-z][A-Za-z0-9-]*)(?:: | #)(?P<value>.*)$")
_BREAKING_TOKENS = frozenset({"BREAKING CHANGE", "BREAKING-CHANGE"})


@dataclass
class ParsedCommit:
    """The structured view of a valid (or partially valid) Conventional Commit message."""

    type: str
    scope: str | None
    description: str
    breaking: bool
    body: str
    footers: list[tuple[str, str]] = field(default_factory=list)

    @property
    def bump(self) -> Bump:
        """The release bump this commit requires on its own."""
        if self.breaking:
            return Bump.MAJOR
        return COMMIT_TYPES[self.type].bump


@dataclass
class ParseResult:
    """Outcome of parsing: the commit when the header was understood, plus every problem found."""

    commit: ParsedCommit | None
    problems: list[Problem]

    @property
    def ok(self) -> bool:
        return self.commit is not None and not self.problems


def _strip_comment_lines(message: str) -> list[str]:
    """Drop git's ``#`` comment lines, which git itself removes when committing with an editor."""
    return [line for line in message.splitlines() if not line.startswith("#")]


def _parse_footers(lines: list[str]) -> list[tuple[str, str]]:
    """Parse the trailing paragraph as footers if *every* logical footer line matches.

    A footer value may continue on following lines until the next token (spec 10), so
    non-matching lines are treated as continuations of the previous footer. If the paragraph
    does not start with a footer token it is ordinary body text and no footers are returned.
    """
    footers: list[tuple[str, str]] = []
    for line in lines:
        match = _FOOTER_RE.match(line)
        if match:
            footers.append((match["token"], match["value"]))
        elif footers:
            token, value = footers[-1]
            footers[-1] = (token, f"{value}\n{line}")
        else:
            return []
    return footers


def parse(message: str) -> ParseResult:
    """Parse and validate ``message``, collecting every problem instead of stopping at the first."""
    problems: list[Problem] = []
    lines = _strip_comment_lines(message.replace("\r\n", "\n"))
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines or not lines[0].strip():
        return ParseResult(None, [Problem(1, "the commit message is empty")])

    header = lines[0]
    if len(header) > MAX_HEADER_LENGTH:
        problems.append(Problem(1, f"the header is {len(header)} characters long; the limit is "
                                   f"{MAX_HEADER_LENGTH}"))
    if header.startswith('Revert "'):
        # git's default revert message; spec does not define reverts, the house rule is "revert:".
        problems.append(Problem(1, 'git\'s default "Revert ..." header is not allowed; use '
                                   '"revert: <original header>" and reference the reverted SHA in '
                                   "the body (\"Refs: <sha>\")"))
        return ParseResult(None, problems)

    match = _HEADER_RE.match(header)
    if match is None:
        problems.append(Problem(1, "the header must look like '<type>(<optional scope>)!: "
                                   "<description>' with exactly one space after the colon"))
        return ParseResult(None, problems)

    commit_type = match["type"]
    if commit_type not in COMMIT_TYPES:
        allowed = ", ".join(COMMIT_TYPES)
        hint = " (types are lowercase)" if commit_type.lower() in COMMIT_TYPES else ""
        problems.append(Problem(1, f"unknown type {commit_type!r}{hint}; allowed types: {allowed}"))

    scope = match["scope"]
    if scope is not None and not _SCOPE_RE.match(scope):
        problems.append(Problem(1, f"invalid scope {scope!r}: use a non-empty lowercase noun such "
                                   "as 'vfs' or 'cli' (letters, digits, '-', '_', '/', '.')"))

    description = match["description"]
    if not description.strip() or description != description.strip():
        problems.append(Problem(1, "the description must be non-empty and must not start or end "
                                   "with whitespace"))

    # spec 6: a body, when present, begins one blank line after the description.
    body_lines: list[str] = []
    footers: list[tuple[str, str]] = []
    if len(lines) > 1:
        if lines[1].strip():
            problems.append(Problem(2, "the header must be followed by a blank line before the body"))
        rest = "\n".join(lines[1:]).strip("\n")
        paragraphs = rest.split("\n\n") if rest else []
        if paragraphs:
            footers = _parse_footers(paragraphs[-1].splitlines())
            body_paragraphs = paragraphs[:-1] if footers else paragraphs
            body_lines = "\n\n".join(body_paragraphs).splitlines()

    breaking = match["breaking"] is not None or any(t in _BREAKING_TOKENS for t, _ in footers)
    if commit_type not in COMMIT_TYPES:
        return ParseResult(None, problems)
    commit = ParsedCommit(
        type=commit_type,
        scope=scope,
        description=description,
        breaking=breaking,
        body="\n".join(body_lines),
        footers=footers,
    )
    return ParseResult(commit, problems)
