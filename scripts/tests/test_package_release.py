"""Tests that release archives have the expected layout and are byte-for-byte reproducible."""

from __future__ import annotations

import contextlib
import io
import os
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import package_release


class PackageReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        for name in package_release.DOCUMENTS:
            (self.root / name).write_text(f"{name}\n", encoding="utf-8")
        (self.root / "bin").write_bytes(b"\x7fELF binary")
        (self.root / "notices.md").write_text("notices\n", encoding="utf-8")

    def build(self, target: str, out: str = "dist", epoch: str = "1767225600") -> Path:
        argv = ["--binary", str(self.root / "bin"), "--target", target, "--version", "1.2.3",
                "--notices", str(self.root / "notices.md"), "--out-dir", str(self.root / out),
                "--root", str(self.root)]
        stdout = io.StringIO()
        with mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": epoch}), \
                contextlib.redirect_stdout(stdout):
            self.assertEqual(package_release.main(argv), 0)
        return Path(stdout.getvalue().strip())

    def test_tar_gz_layout_modes_and_reproducibility(self) -> None:
        first = self.build("x86_64-unknown-linux-gnu")
        self.assertEqual(first.name, "iemod-v1.2.3-x86_64-unknown-linux-gnu.tar.gz")
        with tarfile.open(first) as archive:
            members = {m.name: m for m in archive.getmembers()}
        prefix = "iemod-v1.2.3-x86_64-unknown-linux-gnu/"
        self.assertEqual(sorted(members), sorted(prefix + n for n in (
            "iemod", "LICENSE", "README.md", "CHANGELOG.md", "THIRD_PARTY_NOTICES.md")))
        self.assertEqual(members[prefix + "iemod"].mode, 0o755)
        self.assertEqual({m.mtime for m in members.values()}, {1767225600})
        second = self.build("x86_64-unknown-linux-gnu", out="again")
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_zip_for_windows(self) -> None:
        path = self.build("x86_64-pc-windows-msvc")
        self.assertEqual(path.suffix, ".zip")
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            self.assertIn("iemod-v1.2.3-x86_64-pc-windows-msvc/iemod.exe", names)
            self.assertEqual(archive.read("iemod-v1.2.3-x86_64-pc-windows-msvc/iemod.exe"),
                             b"\x7fELF binary")
        self.assertEqual(path.read_bytes(), self.build("x86_64-pc-windows-msvc", "b").read_bytes())

    def test_missing_document_is_refused(self) -> None:
        (self.root / "LICENSE").unlink()
        with self.assertRaisesRegex(SystemExit, "LICENSE does not exist"):
            self.build("x86_64-unknown-linux-gnu")

    def test_invalid_epoch_and_version_are_refused(self) -> None:
        with self.assertRaisesRegex(SystemExit, "not an integer"):
            self.build("x86_64-unknown-linux-gnu", epoch="yesterday")
        with mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "0"}):
            with self.assertRaisesRegex(SystemExit, "not a valid SemVer"):
                package_release.main(["--binary", "b", "--target", "t", "--version", "v1.2.3",
                                      "--notices", "n", "--out-dir", "d"])

if __name__ == "__main__":
    unittest.main()
