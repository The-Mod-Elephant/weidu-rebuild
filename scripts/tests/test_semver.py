"""Tests for strict SemVer parsing and the project's bump policy."""

from __future__ import annotations

import unittest

from release_tools.bump import Bump
from release_tools.semver import SemverError, Version


class ParseTests(unittest.TestCase):
    def test_valid_versions_round_trip(self) -> None:
        # Examples taken from the SemVer 2.0.0 specification items 9-11.
        for text in ("0.0.0", "1.2.3", "10.20.30", "1.0.0-alpha", "1.0.0-alpha.1",
                     "1.0.0-0.3.7", "1.0.0-x.7.z.92", "1.0.0-x-y-z.--", "1.0.0-alpha+001",
                     "1.0.0+20130313144700", "1.0.0-beta+exp.sha.5114f85"):
            with self.subTest(text=text):
                self.assertEqual(str(Version.parse(text)), text)

    def test_invalid_versions_are_rejected(self) -> None:
        for text in ("", "1", "1.2", "1.2.3.4", "01.2.3", "1.02.3", "1.2.03", "v1.2.3",
                     "1.2.3-", "1.2.3+", "1.2.3-01", "1.2.3-alpha..1", "1.2.3-alpha_1",
                     " 1.2.3", "1.2.3 ", "1.2.3\n", "-1.2.3", "1.2.3-é", "١.2.3"):
            with self.subTest(text=text):
                with self.assertRaises(SemverError):
                    Version.parse(text)

    def test_tag_requires_v_prefix(self) -> None:
        self.assertEqual(Version.from_tag("v1.2.3"), Version(1, 2, 3))
        for tag in ("1.2.3", "V1.2.3", "release-1.2.3", "vv1.2.3"):
            with self.subTest(tag=tag):
                with self.assertRaises(SemverError):
                    Version.from_tag(tag)

    def test_finality(self) -> None:
        self.assertTrue(Version.parse("1.2.3").is_final)
        self.assertFalse(Version.parse("1.2.3-rc.1").is_final)
        self.assertFalse(Version.parse("1.2.3+build").is_final)
        self.assertEqual(Version(1, 2, 3).tag, "v1.2.3")


class BumpTests(unittest.TestCase):
    def test_stable_bumps_follow_semver(self) -> None:
        base = Version(1, 4, 7)
        self.assertEqual(base.bumped(Bump.PATCH), Version(1, 4, 8))
        self.assertEqual(base.bumped(Bump.MINOR), Version(1, 5, 0))
        self.assertEqual(base.bumped(Bump.MAJOR), Version(2, 0, 0))

    def test_initial_development_caps_breaking_changes_at_minor(self) -> None:
        base = Version(0, 3, 2)
        self.assertEqual(base.bumped(Bump.PATCH), Version(0, 3, 3))
        self.assertEqual(base.bumped(Bump.MINOR), Version(0, 4, 0))
        self.assertEqual(base.bumped(Bump.MAJOR), Version(0, 4, 0))

    def test_no_bump_and_non_final_are_errors(self) -> None:
        with self.assertRaises(SemverError):
            Version(1, 0, 0).bumped(Bump.NONE)
        with self.assertRaises(SemverError):
            Version.parse("1.0.0-rc.1").bumped(Bump.PATCH)


if __name__ == "__main__":
    unittest.main()
