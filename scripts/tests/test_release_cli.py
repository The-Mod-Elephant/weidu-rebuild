"""End-to-end tests of ``release.py`` and ``changelog.py`` in a temporary repository."""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import changelog as changelog_cli
import release as release_cli
from tests.git_fixture import TempRepo

ENV = {"GITHUB_SERVER_URL": "https://example.invalid", "GITHUB_REPOSITORY": "owner/repo",
       "GITHUB_ACTIONS": "", "GITHUB_OUTPUT": "", "GITHUB_STEP_SUMMARY": ""}

INITIAL = """\
# Changelog

## [Unreleased]

### Added

- The first feature.

[Unreleased]: https://example.invalid/owner/repo/commits/HEAD
"""


class ReleaseCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepo()
        self.addCleanup(self.repo.cleanup)
        (self.repo.path / "CHANGELOG.md").write_text(INITIAL, encoding="utf-8")
        self.repo.commit("feat: first feature")

    def run_cli(self, module, argv: list[str]) -> tuple[int, str]:
        out = io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(self.repo.path)
            with mock.patch.dict(os.environ, ENV), contextlib.redirect_stdout(out):
                code = module.main(argv)
        finally:
            os.chdir(previous)
        return code, out.getvalue()

    def test_full_release_cycle(self) -> None:
        self.assertEqual(self.run_cli(changelog_cli, ["validate"])[0], 0)
        code, out = self.run_cli(release_cli, ["verify"])
        self.assertEqual(code, 1)
        self.assertIn("still has entries", out)

        self.assertEqual(self.run_cli(changelog_cli, ["prepare", "--date", "2026-01-01"])[0], 0)
        self.assertIn("## [0.1.0] - 2026-01-01",
                      (self.repo.path / "CHANGELOG.md").read_text(encoding="utf-8"))
        # The fixture stages every change, so this also commits the prepared CHANGELOG.md.
        self.repo.commit("docs(changelog): prepare v0.1.0")
        code, out = self.run_cli(release_cli, ["verify"])
        self.assertEqual(code, 0, out)
        self.assertTrue(out.strip().endswith("0.1.0"))

        with tempfile.TemporaryDirectory() as tmp:
            notes = Path(tmp) / "notes.md"
            self.assertEqual(self.run_cli(release_cli, ["notes", "--version", "0.1.0",
                                                        "--output", str(notes)])[0], 0)
            self.assertEqual(notes.read_text(encoding="utf-8"),
                             "### Added\n\n- The first feature.\n\n**Full changelog**: "
                             "https://example.invalid/owner/repo/releases/tag/v0.1.0\n")

        self.repo.tag("v0.1.0")
        self.assertEqual(self.run_cli(changelog_cli, ["validate"])[0], 0)
        code, out = self.run_cli(release_cli, ["verify"])
        self.assertEqual(code, 1)
        self.assertIn("no commit since v0.1.0 requires a release", out)

    def test_prepare_rejects_bad_date_and_notes_unknown_version(self) -> None:
        code, out = self.run_cli(changelog_cli, ["prepare", "--date", "2026-02-30"])
        self.assertEqual(code, 1)
        self.assertIn("changelog prepare failed", out)
        with tempfile.TemporaryDirectory() as tmp:
            code, out = self.run_cli(release_cli, ["notes", "--version", "9.9.9", "--output",
                                                   str(Path(tmp) / "n.md")])
        self.assertEqual(code, 1)
        self.assertIn("no [9.9.9] section", out)

    def test_fix_links_repairs_drift(self) -> None:
        path = self.repo.path / "CHANGELOG.md"
        path.write_text(INITIAL.replace("commits/HEAD", "commits/main"), encoding="utf-8")
        code, out = self.run_cli(changelog_cli, ["validate"])
        self.assertEqual(code, 1)
        self.assertIn("fix-links", out)
        self.assertEqual(self.run_cli(changelog_cli, ["fix-links"])[0], 0)
        self.assertEqual(path.read_text(encoding="utf-8"), INITIAL)


if __name__ == "__main__":
    unittest.main()
