"""Tests that the local cleaner removes only known build output and never escapes the repo."""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

import clean_local
from tests.git_fixture import TempRepo


class CleanLocalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepo()
        self.addCleanup(self.repo.cleanup)
        self.repo.commit("chore: base")
        self.root = self.repo.path.resolve()

    def run_main(self, argv: list[str]) -> str:
        previous = Path.cwd()
        out = io.StringIO()
        try:
            os.chdir(self.root)
            with contextlib.redirect_stdout(out):
                self.assertEqual(clean_local.main(argv), 0)
        finally:
            os.chdir(previous)
        return out.getvalue()

    def test_removes_build_output_and_keeps_everything_else(self) -> None:
        (self.root / "target" / "debug").mkdir(parents=True)
        (self.root / "dist").mkdir()
        (self.root / "scripts" / "__pycache__").mkdir(parents=True)
        (self.root / "scripts" / "keep.py").write_text("x\n")
        (self.root / ".git" / "__pycache__").mkdir()  # must never be touched
        self.assertIn("would remove target", self.run_main(["--dry-run"]))
        self.assertTrue((self.root / "target").exists())
        self.run_main([])
        self.assertFalse((self.root / "target").exists())
        self.assertFalse((self.root / "dist").exists())
        self.assertFalse((self.root / "scripts" / "__pycache__").exists())
        self.assertTrue((self.root / "scripts" / "keep.py").exists())
        self.assertTrue((self.root / ".git" / "__pycache__").exists())

    def test_symlinked_output_dir_is_unlinked_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            victim = Path(outside) / "precious.txt"
            victim.write_text("keep me\n")
            (self.root / "target").symlink_to(outside, target_is_directory=True)
            (self.root / "nested").mkdir()
            (self.root / "nested" / "link").symlink_to(outside, target_is_directory=True)
            Path(outside, "__pycache__").mkdir()
            self.run_main([])
            self.assertFalse((self.root / "target").is_symlink())
            self.assertTrue(victim.exists())
            self.assertTrue(Path(outside, "__pycache__").exists())

    def test_nothing_to_clean(self) -> None:
        self.assertIn("nothing to clean", self.run_main([]))


if __name__ == "__main__":
    unittest.main()
