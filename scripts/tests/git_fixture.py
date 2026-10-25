"""A disposable git repository for tests that exercise real git behaviour."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


class TempRepo:
    """Creates an isolated repository in a temporary directory with deterministic identity.

    Global and system git configuration is disabled (``GIT_CONFIG_GLOBAL``/``GIT_CONFIG_NOSYSTEM``)
    so a contributor's personal settings such as commit signing or hooks cannot change results.
    """

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        self.env = {
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
        self.git("init", "--quiet", "--initial-branch=main")
        self._counter = 0

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.path, env=self.env, check=True,
                              capture_output=True, text=True).stdout

    def commit(self, message: str, path: str | None = None) -> str:
        """Commit a new file change with ``message`` and return the new SHA."""
        self._counter += 1
        target = self.path / (path or f"file{self._counter}.txt")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"change {self._counter}\n", encoding="utf-8")
        self.git("add", "--all")
        self.git("commit", "--quiet", "--no-verify", "--cleanup=verbatim", "-m", message)
        return self.git("rev-parse", "HEAD").strip()

    def tag(self, name: str, annotated: bool = False) -> None:
        if annotated:
            self.git("tag", "-a", name, "-m", name)
        else:
            self.git("tag", name)

    def cleanup(self) -> None:
        self._tmp.cleanup()
