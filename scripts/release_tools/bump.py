"""Version-bump levels shared by commit classification and version computation."""

from __future__ import annotations

import enum


class Bump(enum.IntEnum):
    """How much a change set moves the version number.

    The members are ordered by severity so that the bump required by a whole range of commits is
    simply ``max()`` over the bumps of the individual commits. ``NONE`` means the change does not
    by itself justify a release (for example documentation-only or CI-only commits).
    """

    NONE = 0
    PATCH = 1
    MINOR = 2
    MAJOR = 3
