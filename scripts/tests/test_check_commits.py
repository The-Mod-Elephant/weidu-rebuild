"""End-to-end tests of the commit linter's command-line interface."""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import check_commits
from tests.git_fixture import TempRepo


def run(argv: list[str], cwd: Path, github: bool = False) -> tuple[int, str]:
    """Run the CLI in ``cwd`` and capture stdout; ``github`` simulates an Actions runner."""
    out = io.StringIO()
    env = {"GITHUB_ACTIONS": "true"} if github else {"GITHUB_ACTIONS": ""}
    previous = Path.cwd()
    try:
        os.chdir(cwd)
        with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(out):
            code = check_commits.main(argv)
    finally:
        os.chdir(previous)
    return code, out.getvalue()


class CheckCommitsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepo()
        self.addCleanup(self.repo.cleanup)
        self.base = self.repo.commit("chore: base")

    def test_valid_range_and_title(self) -> None:
        self.repo.commit("feat(cli): add doctor")
        code, out = run(["--base", self.base, "--head", "HEAD", "--title", "feat: add doctor"],
                        self.repo.path)
        self.assertEqual(code, 0, out)
        self.assertIn("All messages follow Conventional Commits.", out)

    def test_invalid_commit_is_annotated_in_ci(self) -> None:
        sha = self.repo.commit("added stuff")
        code, out = run(["--base", self.base, "--head", "HEAD"], self.repo.path, github=True)
        self.assertEqual(code, 1)
        self.assertIn(f"::error title=Commit {sha[:12]}%3A not a Conventional Commit::", out)

    def test_invalid_title(self) -> None:
        code, out = run(["--title", "Update things"], self.repo.path)
        self.assertEqual(code, 1)
        self.assertIn("PR title", out)

    def test_merge_commits_are_skipped(self) -> None:
        self.repo.git("switch", "--quiet", "-c", "topic")
        self.repo.commit("fix: topic")
        self.repo.git("switch", "--quiet", "main")
        self.repo.commit("fix: main")
        self.repo.git("merge", "--quiet", "--no-ff", "-m", "Merge branch 'topic'", "topic")
        code, out = run(["--base", self.base, "--head", "HEAD"], self.repo.path)
        self.assertEqual(code, 0, out)
        self.assertIn("skipped (merge commit)", out)

    def test_bad_range_reports_git_error(self) -> None:
        code, out = run(["--base", "0" * 40, "--head", "HEAD"], self.repo.path)
        self.assertEqual(code, 1)
        self.assertIn("Could not list the pull request commits", out)

    def test_message_file_mode(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("fix x\n")
        self.addCleanup(os.unlink, handle.name)
        code, out = run(["--message-file", handle.name], self.repo.path)
        self.assertEqual(code, 1)
        self.assertIn(f"{handle.name}:1: error:", out)

    def test_usage_error_without_arguments(self) -> None:
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            run([], self.repo.path)


if __name__ == "__main__":
    unittest.main()
