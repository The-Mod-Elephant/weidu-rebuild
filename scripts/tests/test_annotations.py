"""Tests for workflow-command escaping, local rendering, summaries and step outputs."""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from release_tools.annotations import Reporter, write_github_outputs


class ReporterTests(unittest.TestCase):
    def test_github_escaping(self) -> None:
        out = io.StringIO()
        reporter = Reporter(stream=out, github=True)
        reporter.error("100% bad\nsecond line", title="a: b, c", file="dir/x,y.md", line=3)
        self.assertEqual(out.getvalue(),
                         "::error file=dir/x%2Cy.md,line=3,title=a%3A b%2C c::100%25 bad%0Asecond line\n")
        self.assertEqual((reporter.errors, reporter.exit_code), (1, 1))

    def test_local_rendering(self) -> None:
        out = io.StringIO()
        reporter = Reporter(stream=out, github=False)
        reporter.warning("careful", title="Heads up", file="a.md", line=2)
        reporter.error("broken", file="b.md")
        reporter.notice("fyi")
        self.assertEqual(out.getvalue().splitlines(),
                         ["a.md:2: warning: Heads up: careful", "b.md: error: broken",
                          "notice: fyi"])
        self.assertEqual(reporter.warnings, 1)

    def test_summary_goes_to_step_summary_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.md"
            with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(path)}):
                Reporter(stream=io.StringIO(), github=True).summary("# Title\n")
            self.assertEqual(path.read_text(encoding="utf-8"), "# Title\n\n")


class OutputTests(unittest.TestCase):
    def test_single_and_multiline_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out"
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(path)}):
                write_github_outputs({"a": "1", "b": "x\nEOF_RELEASE_TOOLS\ny"})
            self.assertEqual(path.read_text(encoding="utf-8"),
                             "a=1\nb<<EOF_RELEASE_TOOLS_\nx\nEOF_RELEASE_TOOLS\ny\n"
                             "EOF_RELEASE_TOOLS_\n")

    def test_no_output_file_is_a_no_op(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": ""}):
            write_github_outputs({"a": "1"})


if __name__ == "__main__":
    unittest.main()
