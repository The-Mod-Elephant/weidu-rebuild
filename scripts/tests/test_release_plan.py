"""Tests for version planning and release readiness against real temporary git repositories."""

from __future__ import annotations

import subprocess
import unittest

from release_tools.bump import Bump
from release_tools.changelog import Changelog
from release_tools.git import Git
from release_tools.release_plan import PlanError, check_readiness, plan
from release_tools.semver import Version
from tests.git_fixture import TempRepo

REPO = "https://example.invalid/owner/repo"


def changelog(*sections: tuple[str, str]) -> Changelog:
    """Build a canonical changelog with an empty Unreleased section and the given releases."""
    text = "# Changelog\n\n## [Unreleased]\n\n"
    for version, date in sections:
        text += f"## [{version}] - {date}\n\n### Added\n\n- Something.\n\n"
    parsed = Changelog.parse(text)
    parsed.links = {k: (v, 0) for k, v in parsed.expected_links(REPO).items()}
    return Changelog.parse(parsed.render())


class PlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepo()
        self.addCleanup(self.repo.cleanup)
        self.git = Git(self.repo.path)

    def test_first_release_is_0_1_0_and_tolerates_old_history(self) -> None:
        self.repo.commit("Initial commit")
        self.repo.commit("docs: readme")
        release = plan(self.git)
        self.assertEqual((release.previous, release.next), (None, Version(0, 1, 0)))
        self.assertEqual(len(release.nonconforming), 1)
        self.assertEqual(len(release.commits), 1)

    def test_bumps_from_latest_reachable_final_tag(self) -> None:
        self.repo.commit("feat: one")
        self.repo.tag("v0.1.0")
        self.repo.commit("fix: two")
        self.repo.tag("v0.1.1", annotated=True)  # annotated tags must peel to their commit
        self.repo.commit("fix: three")
        self.repo.tag("v0.2.0-rc.1")  # pre-releases never count as the current version
        self.repo.tag("nightly")
        release = plan(self.git)
        self.assertEqual(release.previous, Version(0, 1, 1))
        self.assertEqual(release.next, Version(0, 1, 2))
        self.assertEqual(sorted(release.ignored_tags), ["nightly", "v0.2.0-rc.1"])

    def test_highest_bump_wins(self) -> None:
        self.repo.commit("feat: base")
        self.repo.tag("v1.2.3")
        self.repo.commit("fix: a")
        self.repo.commit("feat(cli): b")
        self.repo.commit("docs: c")
        self.assertEqual(plan(self.git).next, Version(1, 3, 0))
        self.repo.commit("refactor!: d")
        release = plan(self.git)
        self.assertEqual((release.bump, release.next), (Bump.MAJOR, Version(2, 0, 0)))

    def test_breaking_change_in_0x_bumps_minor(self) -> None:
        self.repo.commit("feat: base")
        self.repo.tag("v0.4.2")
        self.repo.commit("fix: x\n\nBREAKING CHANGE: y")
        self.assertEqual(plan(self.git).next, Version(0, 5, 0))

    def test_unreachable_tags_are_ignored(self) -> None:
        self.repo.commit("feat: base")
        self.repo.tag("v0.1.0")
        self.repo.git("switch", "--quiet", "-c", "side")
        self.repo.commit("feat: side")
        self.repo.tag("v0.9.0")
        self.repo.git("switch", "--quiet", "main")
        self.repo.commit("fix: main")
        self.assertEqual(plan(self.git).next, Version(0, 1, 1))

    def test_errors(self) -> None:
        self.repo.commit("feat: base")
        self.repo.tag("v0.1.0")
        self.repo.commit("docs: only docs")
        with self.assertRaisesRegex(PlanError, "no commit since v0.1.0 requires a release"):
            plan(self.git)
        self.repo.commit("bad message")
        with self.assertRaisesRegex(PlanError, "not Conventional Commits"):
            plan(self.git)

    def test_shallow_clone_is_rejected(self) -> None:
        self.repo.commit("feat: a")
        self.repo.commit("feat: b")
        clone = TempRepo()
        self.addCleanup(clone.cleanup)
        subprocess.run(["git", "clone", "--quiet", "--depth=1", f"file://{self.repo.path}",
                        str(clone.path / "c")], check=True, env=clone.env, capture_output=True)
        with self.assertRaisesRegex(PlanError, "shallow"):
            plan(Git(clone.path / "c"))

    def test_messages_with_unusual_bytes_are_read_exactly(self) -> None:
        message = "fix: unusual\n\nbody with \x1e record separator and ünïcödé"
        self.repo.commit(message)
        self.assertEqual(self.git.commits("HEAD")[0].message, message)


class ReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepo()
        self.addCleanup(self.repo.cleanup)
        self.git = Git(self.repo.path)
        self.repo.commit("feat: base")
        self.repo.tag("v0.1.0")
        self.repo.commit("feat: next")

    def test_prepared_matching_section_is_ready(self) -> None:
        release = plan(self.git)
        version, problems = check_readiness(
            release, changelog(("0.2.0", "2026-02-01"), ("0.1.0", "2026-01-01")),
            self.git.tags(), REPO)
        self.assertEqual((version, problems), (Version(0, 2, 0), []))

    def test_mismatched_or_missing_section(self) -> None:
        release = plan(self.git)
        version, problems = check_readiness(
            release, changelog(("0.1.1", "2026-02-01"), ("0.1.0", "2026-01-01")),
            self.git.tags(), REPO)
        self.assertIsNone(version)
        self.assertIn("require [0.2.0]", " ".join(p.message for p in problems))
        version, problems = check_readiness(release, changelog(("0.1.0", "2026-01-01")),
                                            self.git.tags(), REPO)
        self.assertIsNone(version)
        self.assertIn("no '## [0.2.0]' section has been prepared",
                      " ".join(p.message for p in problems))

    def test_existing_tag_for_prepared_version(self) -> None:
        # A v0.2.0 tag that is not reachable from HEAD (for example created on another branch)
        # does not influence the plan, but must still block releasing 0.2.0 a second time.
        self.repo.git("switch", "--quiet", "-c", "side", "HEAD~1")
        self.repo.commit("fix: side")
        self.repo.tag("v0.2.0")
        self.repo.git("switch", "--quiet", "main")
        release = plan(self.git)
        self.assertEqual(release.next, Version(0, 2, 0))
        version, problems = check_readiness(
            release, changelog(("0.2.0", "2026-02-01"), ("0.1.0", "2026-01-01")),
            self.git.tags(), REPO)
        self.assertIsNone(version)
        self.assertIn("tag v0.2.0 already exists", " ".join(p.message for p in problems))

    def test_unreleased_entries_block_release(self) -> None:
        doc = changelog(("0.2.0", "2026-02-01"), ("0.1.0", "2026-01-01"))
        assert doc.unreleased is not None
        doc.unreleased.body = ["", "### Fixed", "", "- Pending."]
        _, problems = check_readiness(plan(self.git), doc, self.git.tags(), REPO)
        self.assertIn("still has entries", " ".join(p.message for p in problems))

    def test_explicit_graduation_to_1_0_0(self) -> None:
        version, problems = check_readiness(
            plan(self.git), changelog(("1.0.0", "2026-02-01"), ("0.1.0", "2026-01-01")),
            self.git.tags(), REPO)
        self.assertEqual((version, problems), (Version(1, 0, 0), []))


if __name__ == "__main__":
    unittest.main()
