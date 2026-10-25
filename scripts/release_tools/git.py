"""A thin, explicit wrapper around the ``git`` command line.

Only read-only plumbing is used here. Each failure is turned into a ``GitError`` that carries
the exact command and git's own stderr, so CI logs say *why* git failed (for example a shallow
clone missing history) instead of only reporting a non-zero exit status.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

class GitError(RuntimeError):
    """A git invocation failed; the message includes the command line and git's stderr."""


@dataclass(frozen=True)
class Commit:
    """One commit as needed by the linters and the release planner."""

    sha: str
    parents: tuple[str, ...]
    message: str

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1

    @property
    def short(self) -> str:
        return self.sha[:12]


@dataclass(frozen=True)
class Git:
    """Runs git inside one repository working tree."""

    cwd: Path

    def run_bytes(self, *args: str, stdin: bytes | None = None) -> bytes:
        """Run ``git <args>`` and return raw stdout, raising ``GitError`` with context on failure."""
        command = ["git", *args]
        try:
            completed = subprocess.run(
                command, cwd=self.cwd, check=False, capture_output=True, input=stdin
            )
        except FileNotFoundError as exc:
            raise GitError("the 'git' executable was not found on PATH") from exc
        if completed.returncode != 0:
            stderr = completed.stderr.decode("utf-8", errors="replace").strip()
            raise GitError(
                f"`{' '.join(command)}` exited with status {completed.returncode}: "
                f"{stderr or '(no stderr output)'}"
            )
        return completed.stdout

    def run(self, *args: str) -> str:
        """Run ``git <args>`` and return stdout decoded as UTF-8."""
        return self.run_bytes(*args).decode("utf-8", errors="replace")

    def toplevel(self) -> Path:
        """Absolute path of the working tree root."""
        return Path(self.run("rev-parse", "--show-toplevel").strip())

    def is_shallow(self) -> bool:
        """True in a shallow clone, where history-based computations would silently be wrong."""
        return self.run("rev-parse", "--is-shallow-repository").strip() == "true"

    def resolve(self, rev: str) -> str:
        """Resolve a revision expression to a full commit SHA (``^{commit}`` peels tags)."""
        return self.run("rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}").strip()

    def tags(self) -> list[str]:
        """All tag names in the repository."""
        return [line for line in self.run("tag", "--list").splitlines() if line]

    def tags_merged_into(self, rev: str) -> list[str]:
        """Tags whose commits are ancestors of (or equal to) ``rev``."""
        return [line for line in self.run("tag", "--list", "--merged", rev).splitlines() if line]

    def commits(self, rev_range: str) -> list[Commit]:
        """Commits in ``rev_range`` (``A..B`` or a single rev for all history), oldest first.

        ``rev-list --parents`` yields "<sha> <parent>..." per line. Messages are then read with
        one ``cat-file --batch`` process, whose output is length-prefixed, so parsing is exact
        no matter what bytes a commit message contains.
        """
        lines = self.run("rev-list", "--reverse", "--parents", rev_range).splitlines()
        if not lines:
            return []
        shas = [line.split()[0] for line in lines]
        raw = self.run_bytes("cat-file", "--batch", stdin="".join(f"{s}\n" for s in shas).encode())
        commits = []
        offset = 0
        for line in lines:
            sha, *parents = line.split()
            # Batch header: "<sha> <type> <size>\n", then <size> bytes of object, then "\n".
            header_end = raw.index(b"\n", offset)
            _, obj_type, size = raw[offset:header_end].decode("ascii").split()
            if obj_type != "commit":
                raise GitError(f"expected a commit object for {sha}, got {obj_type}")
            body_start = header_end + 1
            body = raw[body_start : body_start + int(size)]
            offset = body_start + int(size) + 1
            # A commit object is "<headers>\n\n<message>"; headers never contain an empty line
            # (multi-line headers such as gpgsig continue with a leading space).
            _, _, message = body.partition(b"\n\n")
            commits.append(
                Commit(sha, tuple(parents), message.decode("utf-8", errors="replace").rstrip("\n"))
            )
        return commits

    def changed_files(self, base: str, head: str) -> list[str]:
        """Paths changed between the merge base of ``base`` and ``head``, and ``head``."""
        output = self.run("diff", "--name-only", "-z", f"{base}...{head}")
        return [path for path in output.split("\0") if path]

    def remote_url(self, remote: str = "origin") -> str:
        """The fetch URL of ``remote``."""
        return self.run("remote", "get-url", remote).strip()
