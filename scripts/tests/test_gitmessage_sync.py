"""Guards that the documented commit types never drift from ``commit_types.COMMIT_TYPES``."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from release_tools.commit_types import COMMIT_TYPES

ROOT = Path(__file__).resolve().parents[2]
# Template lines look like "#   feat:     A new user-facing feature [minor]".
_TYPE_LINE = re.compile(r"^#\s{3}(?P<type>[a-z]+):\s+(?P<description>.+?) \[(?P<bump>\w+)\]$")


class GitmessageSyncTests(unittest.TestCase):
    def test_template_lists_exactly_the_allowed_types_in_order(self) -> None:
        text = (ROOT / ".gitmessage").read_text(encoding="utf-8")
        documented = [m.groupdict() for m in map(_TYPE_LINE.match, text.splitlines()) if m]
        expected = [{"type": name, "description": t.description, "bump": t.bump.name.lower()}
                    for name, t in COMMIT_TYPES.items()]
        self.assertEqual(documented, expected)

    def test_template_lines_are_all_comments(self) -> None:
        # Every non-empty template line must start with "#" so git strips it from the message.
        text = (ROOT / ".gitmessage").read_text(encoding="utf-8")
        self.assertEqual([line for line in text.splitlines() if line and not line.startswith("#")],
                         [])

    def test_contributing_lists_every_type(self) -> None:
        text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        for name in COMMIT_TYPES:
            with self.subTest(type=name):
                self.assertIn(f"| `{name}` |", text)


if __name__ == "__main__":
    unittest.main()
