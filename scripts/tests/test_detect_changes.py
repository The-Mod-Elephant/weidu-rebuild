"""Tests for CI change classification and its fail-open behaviour."""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import detect_changes
from tests.git_fixture import TempRepo


class ClassifyTests(unittest.TestCase):
    def test_groups(self) -> None:
        cases = {
            ("crates/iemod-vfs/src/lib.rs",): {"rust"},
            ("Cargo.lock",): {"rust"},
            ("crates-old/x.rs",): set(),
            ("scripts/release.py",): {"python"},
            ("CHANGELOG.md",): {"python"},
            (".github/workflows/release.yml",): {"workflows"},
            (".github/dependabot.yml",): {"workflows"},
            ("README.md", "docs/adr/0001-rust.md"): set(),
            (".github/workflows/ci.yml",): {"rust", "python", "workflows"},
            ("scripts/detect_changes.py",): {"rust", "python", "workflows"},
        }
        for paths, expected in cases.items():
            with self.subTest(paths=paths):
                result = detect_changes.classify(list(paths))
                self.assertEqual({g for g, run in result.items() if run}, expected)


class MainTests(unittest.TestCase):
    def run_main(self, argv: list[str], cwd: Path) -> dict[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            previous = Path.cwd()
            try:
                os.chdir(cwd)
                with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output),
                                                  "GITHUB_ACTIONS": ""}), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(detect_changes.main(argv), 0)
            finally:
                os.chdir(previous)
            return dict(line.split("=", 1) for line in output.read_text().splitlines())

    def setUp(self) -> None:
        self.repo = TempRepo()
        self.addCleanup(self.repo.cleanup)
        self.base = self.repo.commit("chore: base")

    def test_diff_against_base(self) -> None:
        self.repo.commit("fix: x", "scripts/x.py")
        self.assertEqual(self.run_main(["--base", self.base, "--head", "HEAD"], self.repo.path),
                         {"rust": "false", "python": "true", "workflows": "false"})

    def test_unknown_or_broken_base_runs_everything(self) -> None:
        everything = {"rust": "true", "python": "true", "workflows": "true"}
        for base in ("", "0" * 40, "f" * 40):
            with self.subTest(base=base):
                self.assertEqual(self.run_main(["--base", base, "--head", "HEAD"], self.repo.path),
                                 everything)


if __name__ == "__main__":
    unittest.main()
