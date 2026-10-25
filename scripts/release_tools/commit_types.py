"""The single source of truth for the Conventional Commit types this repository accepts.

Every consumer reads this table: the commit linter (``scripts/check_commits.py``), the version
planner (``release_tools.release_plan``), and a unit test that asserts ``.gitmessage`` documents
exactly these types. Adding or removing a type therefore only requires editing this file, the
commit template, and ``CONTRIBUTING.md`` (the test enforces the template; review enforces the
guide).

The type names are those of ``@commitlint/config-conventional`` (based on the Angular
convention), which the Conventional Commits 1.0.0 specification cites as an example set of types
beyond ``feat`` and ``fix``. The specification itself
only mandates the meaning of ``feat`` (a new feature, correlates with a SemVer MINOR) and ``fix``
(a bug fix, correlates with a SemVer PATCH); the bump assigned to the remaining types is this
project's policy and is documented in ``CONTRIBUTING.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from release_tools.bump import Bump


@dataclass(frozen=True)
class CommitType:
    """One allowed commit type: its human description and the release bump it implies."""

    description: str
    bump: Bump


# MappingProxyType makes the table read-only at runtime so no caller can mutate the policy.
# Insertion order is the order shown to contributors in error messages and documentation.
COMMIT_TYPES: Mapping[str, CommitType] = MappingProxyType(
    {
        "feat": CommitType("A new user-facing feature", Bump.MINOR),
        "fix": CommitType("A user-facing bug fix", Bump.PATCH),
        "perf": CommitType("A change that improves performance", Bump.PATCH),
        # A revert undoes previously released behaviour, so it must reach users as a release.
        "revert": CommitType("Reverts a previous commit", Bump.PATCH),
        "refactor": CommitType("A code change that neither fixes a bug nor adds a feature", Bump.NONE),
        "docs": CommitType("Documentation only changes", Bump.NONE),
        "style": CommitType("Formatting changes that do not affect meaning", Bump.NONE),
        "test": CommitType("Adding or correcting tests", Bump.NONE),
        "build": CommitType("Build system, toolchain or dependency changes", Bump.NONE),
        "ci": CommitType("CI configuration and workflow changes", Bump.NONE),
        "chore": CommitType("Maintenance that does not touch shipped code", Bump.NONE),
    }
)
