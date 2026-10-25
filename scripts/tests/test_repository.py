"""Tests for deriving the web URL from git remotes and Actions variables."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from release_tools.git import Git
from release_tools.repository import RepositoryUrlError, normalise_remote, repository_url
from tests.git_fixture import TempRepo


class RepositoryUrlTests(unittest.TestCase):
    def test_remote_forms(self) -> None:
        expected = "https://github.com/owner/repo"
        for remote in ("https://github.com/owner/repo.git", "https://github.com/owner/repo",
                       "https://github.com/owner/repo/", "git@github.com:owner/repo.git",
                       "ssh://git@github.com/owner/repo.git", "ssh://git@github.com:22/owner/repo",
                       "https://x-access-token:secret@github.com/owner/repo.git"):
            with self.subTest(remote=remote):
                self.assertEqual(normalise_remote(remote), expected)

    def test_unrecognised_remote(self) -> None:
        for remote in ("", "/local/path/repo", "file:///tmp/repo"):
            with self.subTest(remote=remote):
                with self.assertRaises(RepositoryUrlError):
                    normalise_remote(remote)

    def test_actions_variables_take_precedence(self) -> None:
        repo = TempRepo()
        self.addCleanup(repo.cleanup)
        with mock.patch.dict(os.environ, {"GITHUB_SERVER_URL": "https://ghe.example/",
                                          "GITHUB_REPOSITORY": "org/name"}):
            self.assertEqual(repository_url(Git(repo.path)), "https://ghe.example/org/name")
        repo.git("remote", "add", "origin", "git@github.com:a/b.git")
        with mock.patch.dict(os.environ, {"GITHUB_SERVER_URL": "", "GITHUB_REPOSITORY": ""}):
            self.assertEqual(repository_url(Git(repo.path)), "https://github.com/a/b")


if __name__ == "__main__":
    unittest.main()
