"""Tests for the CHANGELOG.md model (parse, render, prepare) and its validation rules."""

from __future__ import annotations

import textwrap
import unittest

from release_tools.changelog import Changelog, ChangelogError
from release_tools.changelog_validation import validate
from release_tools.semver import Version

REPO = "https://example.invalid/owner/repo"

PREAMBLE = """\
# Changelog

All notable changes to this project will be documented in this file.
"""


def doc(body: str) -> Changelog:
    return Changelog.parse(PREAMBLE + "\n" + textwrap.dedent(body))


VALID = """\
## [Unreleased]

## [0.2.0] - 2026-02-01

### Added

- Second feature.

## [0.1.0] - 2026-01-01

### Added

- First feature.

[Unreleased]: https://example.invalid/owner/repo/compare/v0.2.0...HEAD
[0.2.0]: https://example.invalid/owner/repo/compare/v0.1.0...v0.2.0
[0.1.0]: https://example.invalid/owner/repo/releases/tag/v0.1.0
"""


def messages(changelog: Changelog, tags: list[str] | None = None) -> str:
    return " | ".join(p.message for p in validate(changelog, REPO, tags))


class ModelTests(unittest.TestCase):
    def test_render_round_trips_a_canonical_file(self) -> None:
        text = PREAMBLE + "\n" + VALID
        self.assertEqual(Changelog.parse(text).render(), text)

    def test_parse_errors(self) -> None:
        for text, fragment in (
            ("# Changelog\n\n## Unreleased\n", "release headings"),
            ("# Changelog\n\n[a]: x\n[A]: y\n", "duplicate link"),
            ("# Changelog\n\n[a]: x\n\nmore text\n", "must be the last lines"),
        ):
            with self.subTest(text=text):
                with self.assertRaisesRegex(ChangelogError, fragment):
                    Changelog.parse(text)

    def test_prepare_promotes_unreleased_and_regenerates_links(self) -> None:
        changelog = doc("""\
            ## [Unreleased]

            ### Fixed

            - A bug.

            ## [0.1.0] - 2026-01-01

            ### Added

            - First feature.

            [Unreleased]: https://example.invalid/owner/repo/compare/v0.1.0...HEAD
            [0.1.0]: https://example.invalid/owner/repo/releases/tag/v0.1.0
            """)
        changelog.prepare(Version(0, 1, 1), "2026-03-01", REPO)
        rendered = changelog.render()
        self.assertIn("## [Unreleased]\n\n## [0.1.1] - 2026-03-01\n\n### Fixed\n\n- A bug.", rendered)
        self.assertIn("[Unreleased]: https://example.invalid/owner/repo/compare/v0.1.1...HEAD",
                      rendered)
        self.assertIn("[0.1.1]: https://example.invalid/owner/repo/compare/v0.1.0...v0.1.1",
                      rendered)
        self.assertEqual(messages(Changelog.parse(rendered)), "")

    def test_prepare_first_release_and_refusals(self) -> None:
        changelog = doc("## [Unreleased]\n\n### Added\n\n- Everything.\n\n"
                        "[Unreleased]: https://example.invalid/owner/repo/commits/HEAD\n")
        changelog.prepare(Version(0, 1, 0), "2026-01-01", REPO)
        self.assertIn("[0.1.0]: https://example.invalid/owner/repo/releases/tag/v0.1.0",
                      changelog.render())
        with self.assertRaisesRegex(ChangelogError, "no entries"):
            changelog.prepare(Version(0, 2, 0), "2026-01-02", REPO)
        with self.assertRaisesRegex(ChangelogError, "no '## \\[Unreleased\\]'"):
            Changelog.parse("# Changelog\n").prepare(Version(0, 1, 0), "2026-01-01", REPO)

    def test_prepare_rejects_existing_version(self) -> None:
        changelog = Changelog.parse(PREAMBLE + "\n" + VALID.replace(
            "## [Unreleased]\n", "## [Unreleased]\n\n### Fixed\n\n- x.\n"))
        with self.assertRaisesRegex(ChangelogError, "already exists"):
            changelog.prepare(Version(0, 2, 0), "2026-03-01", REPO)


class ValidationTests(unittest.TestCase):
    def test_valid_file_with_matching_tags(self) -> None:
        self.assertEqual(messages(doc(VALID), ["v0.1.0", "v0.2.0", "not-a-version"]), "")

    def test_untagged_top_section_is_allowed_but_not_lower_ones(self) -> None:
        self.assertEqual(messages(doc(VALID), ["v0.1.0"]), "")
        self.assertIn("no matching tag v0.1.0", messages(doc(VALID), ["v0.2.0"]))

    def test_tag_without_section(self) -> None:
        self.assertIn("tag v0.3.0 has no", messages(doc(VALID), ["v0.1.0", "v0.2.0", "v0.3.0"]))
        # Pre-release tags are not releases and need no section.
        self.assertEqual(messages(doc(VALID), ["v0.1.0", "v0.2.0", "v0.3.0-rc.1"]), "")

    def test_structural_problems(self) -> None:
        # (text to replace in the full document, replacement, expected message fragment)
        cases = {
            "missing title": ("# Changelog", "# Change log", "# Changelog"),
            "unreleased not first": ("## [Unreleased]\n\n## [0.2.0] - 2026-02-01\n",
                                     "## [0.2.0] - 2026-02-01\n\n- x.\n\n## [Unreleased]\n",
                                     "first section"),
            "missing date": ("## [0.2.0] - 2026-02-01", "## [0.2.0]", "ISO 8601"),
            "bad date": ("2026-02-01", "2026-02-30", "real calendar date"),
            "non iso date": ("2026-02-01", "01/02/2026", "ISO 8601"),
            "order": ("## [0.2.0] - 2026-02-01", "## [0.0.9] - 2026-02-01", "must be lower"),
            "date order": ("## [0.1.0] - 2026-01-01", "## [0.1.0] - 2026-03-01", "dated after"),
            "prerelease": ("## [0.2.0] - 2026-02-01", "## [0.2.0-rc.1] - 2026-02-01",
                           "final release"),
            "bad type": ("### Added\n\n- Second", "### New\n\n- Second", "unknown change type"),
            "empty release": ("- Second feature.\n", "", "has no entries"),
            "unreleased date": ("## [Unreleased]", "## [Unreleased] - 2026-01-01", "no date"),
        }
        full = PREAMBLE + "\n" + VALID
        for name, (old, new, fragment) in cases.items():
            with self.subTest(name=name):
                self.assertIn(old, full)
                self.assertIn(fragment, messages(Changelog.parse(full.replace(old, new, 1))))

    def test_duplicate_subsection_and_version(self) -> None:
        dup_type = VALID.replace("- Second feature.\n", "- Second feature.\n\n### Added\n\n- b.\n")
        self.assertIn("appears twice", messages(doc(dup_type)))
        dup_version = VALID.replace("## [0.1.0] - 2026-01-01", "## [0.2.0] - 2026-01-01")
        self.assertIn("more than once", messages(doc(dup_version)))

    def test_links_must_be_canonical(self) -> None:
        wrong = VALID.replace("compare/v0.2.0...HEAD", "compare/v0.1.0...HEAD")
        self.assertIn("[Unreleased] must link to", messages(doc(wrong)))
        extra = VALID + "[0.0.1]: https://example.invalid/x\n"
        self.assertIn("does not correspond", messages(doc(extra)))
        missing = VALID.replace("[0.1.0]: https://example.invalid/owner/repo/releases/tag/v0.1.0\n",
                                "")
        self.assertIn("[0.1.0] must link to", messages(doc(missing)))

    def test_exactly_one_unreleased(self) -> None:
        self.assertIn("exactly one", messages(doc(VALID.replace("## [Unreleased]\n", ""))))


if __name__ == "__main__":
    unittest.main()
