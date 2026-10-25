"""Discovery of the repository's canonical web URL, used to build changelog compare links.

Nothing about the hosting location is hard-coded. In GitHub Actions the URL comes from the
default ``GITHUB_SERVER_URL`` and ``GITHUB_REPOSITORY`` variables that every job receives; locally
it is derived from the ``origin`` remote, accepting the HTTPS and SSH forms git hosts hand out.
"""

from __future__ import annotations

import os
import re

from release_tools.git import Git

# scp-like SSH syntax ("git@host:owner/repo.git") and URL syntax ("https://host/owner/repo.git",
# "ssh://git@host/owner/repo"). Credentials embedded in HTTPS remotes ("https://token@host/...")
# are dropped by only capturing host and path, so they can never leak into a generated link.
_SCP_RE = re.compile(r"^[^@/\s]+@(?P<host>[^:/\s]+):(?P<path>[^\s]+?)(?:\.git)?/?$")
_URL_RE = re.compile(r"^(?:https?|ssh|git)://(?:[^@/\s]+@)?(?P<host>[^:/\s]+)(?::\d+)?/"
                     r"(?P<path>[^\s]+?)(?:\.git)?/?$")


class RepositoryUrlError(RuntimeError):
    """The repository URL could not be determined."""


def normalise_remote(remote: str) -> str:
    """Convert a git remote URL into the ``https://host/owner/repo`` web URL."""
    for pattern in (_SCP_RE, _URL_RE):
        match = pattern.match(remote.strip())
        if match:
            return f"https://{match['host']}/{match['path']}"
    raise RepositoryUrlError(f"cannot derive a web URL from the git remote {remote!r}")


def repository_url(git: Git) -> str:
    """The canonical web URL of this repository, without a trailing slash."""
    server = os.environ.get("GITHUB_SERVER_URL")
    repository = os.environ.get("GITHUB_REPOSITORY")
    if server and repository:
        return f"{server.rstrip('/')}/{repository}"
    return normalise_remote(git.remote_url())
