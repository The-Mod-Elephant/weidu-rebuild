"""The common shape of a validation failure reported by every checker in this package."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Problem:
    """A single validation failure, located by a 1-based line number within its input."""

    line: int
    message: str
