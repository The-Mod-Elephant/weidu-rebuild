"""Tests for Conventional Commits parsing, including the specification's own examples."""

from __future__ import annotations

import unittest

from release_tools import conventional
from release_tools.bump import Bump
from release_tools.conventional import MAX_HEADER_LENGTH


class ValidMessageTests(unittest.TestCase):
    def assert_valid(self, message: str) -> conventional.ParsedCommit:
        result = conventional.parse(message)
        self.assertEqual(result.problems, [], message)
        assert result.commit is not None
        return result.commit

    def test_spec_examples(self) -> None:
        # The "Examples" section of https://www.conventionalcommits.org/en/v1.0.0/.
        commit = self.assert_valid("feat: allow provided config object to extend other configs\n\n"
                                   "BREAKING CHANGE: `extends` key in config file is now used for "
                                   "extending other config files")
        self.assertTrue(commit.breaking)
        self.assertTrue(self.assert_valid("feat!: send an email to the customer when a product "
                                          "is shipped").breaking)
        commit = self.assert_valid("feat(api)!: send an email to the customer when a product is "
                                   "shipped")
        self.assertEqual((commit.scope, commit.breaking), ("api", True))
        self.assertTrue(self.assert_valid("chore!: drop support for Node 6\n\nBREAKING CHANGE: "
                                          "use JavaScript features not available in Node 6.")
                        .breaking)
        self.assertEqual(self.assert_valid("docs: correct spelling of CHANGELOG").bump, Bump.NONE)
        self.assertEqual(self.assert_valid("feat(lang): add Polish language").scope, "lang")
        commit = self.assert_valid(
            "fix: prevent racing of requests\n\nIntroduce a request id and a reference to latest "
            "request. Dismiss\nincoming responses other than from latest request.\n\nRemove "
            "timeouts which were used to mitigate the racing issue but are\nobsolete now.\n\n"
            "Reviewed-by: Z\nRefs: #123")
        self.assertEqual(commit.footers, [("Reviewed-by", "Z"), ("Refs", "#123")])
        self.assertIn("obsolete now.", commit.body)
        self.assertFalse(commit.breaking)

    def test_bumps(self) -> None:
        self.assertEqual(self.assert_valid("feat: x").bump, Bump.MINOR)
        self.assertEqual(self.assert_valid("fix: x").bump, Bump.PATCH)
        self.assertEqual(self.assert_valid("perf: x").bump, Bump.PATCH)
        self.assertEqual(self.assert_valid("revert: feat: x").bump, Bump.PATCH)
        self.assertEqual(self.assert_valid("ci: x").bump, Bump.NONE)
        self.assertEqual(self.assert_valid("ci!: x").bump, Bump.MAJOR)

    def test_breaking_change_footer_variants(self) -> None:
        self.assertTrue(self.assert_valid("fix: x\n\nBREAKING-CHANGE: y").breaking)
        self.assertTrue(self.assert_valid("fix: x\n\nRefs: #1\nBREAKING CHANGE: y\n  more").breaking)
        # Lowercase is not the reserved token (spec 15), so it is an ordinary footer.
        self.assertFalse(self.assert_valid("fix: x\n\nbreaking-change: y").breaking)
        # A "BREAKING CHANGE:" inside a body paragraph is not a footer.
        self.assertFalse(self.assert_valid("fix: x\n\nWe avoid a BREAKING CHANGE: here.\n\n"
                                           "Refs: #2").breaking)

    def test_hash_separator_footer_and_comment_lines(self) -> None:
        commit = self.assert_valid("fix: x\n# a git comment line\n\nFixes #42\n")
        self.assertEqual(commit.footers, [("Fixes", "42")])

    def test_crlf_and_trailing_blank_lines(self) -> None:
        self.assert_valid("fix(cli): x\r\n\r\nbody\r\n\r\n\r\n")

    def test_scopes(self) -> None:
        for scope in ("vfs", "iemod-cli", "deps_dev", "release/notes", "v1.2"):
            with self.subTest(scope=scope):
                self.assert_valid(f"fix({scope}): x")

    def test_header_length_limit_is_inclusive(self) -> None:
        header = "fix: " + "a" * (MAX_HEADER_LENGTH - len("fix: "))
        self.assert_valid(header)


class InvalidMessageTests(unittest.TestCase):
    def assert_invalid(self, message: str, fragment: str) -> None:
        result = conventional.parse(message)
        self.assertFalse(result.ok, message)
        joined = " | ".join(p.message for p in result.problems)
        self.assertIn(fragment, joined)

    def test_cases(self) -> None:
        cases = {
            "": "empty",
            "\n\n": "empty",
            "# only a comment": "empty",
            "Add feature": "header must look like",
            "feat:missing space": "header must look like",
            "feat:  two spaces": "must not start or end",
            "feat: ": "non-empty",
            "feat: trailing ": "must not start or end",
            "feature: x": "unknown type 'feature'",
            "Feat: x": "types are lowercase",
            "feat(): x": "invalid scope",
            "feat(Vfs): x": "invalid scope",
            "feat(a b): x": "invalid scope",
            "feat(a)(b): x": "header must look like",
            "feat!(a): x": "header must look like",
            "fix: x\nno blank line": "blank line",
            'Revert "feat: x"': "Revert",
            "fix: " + "a" * MAX_HEADER_LENGTH: "characters long",
        }
        for message, fragment in cases.items():
            with self.subTest(message=message):
                self.assert_invalid(message, fragment)

    def test_all_problems_are_reported(self) -> None:
        result = conventional.parse("Feat(X): " + "a" * MAX_HEADER_LENGTH + "\nbody")
        self.assertGreaterEqual(len(result.problems), 4)


if __name__ == "__main__":
    unittest.main()
