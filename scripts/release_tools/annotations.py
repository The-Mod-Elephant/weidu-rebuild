"""Diagnostics that render as GitHub Actions annotations in CI and as plain text locally.

GitHub turns specially formatted stdout lines ("workflow commands") into annotations attached to
a file and line in the pull request, which is far clearer than a bare non-zero exit code. See
https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands. The
escaping rules implemented below mirror the reference implementation in the ``@actions/core``
toolkit (``command.ts``): message data escapes ``%``, CR and LF; property values additionally
escape ``:`` and ``,`` because those characters delimit properties.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import TextIO


def _escape_data(value: str) -> str:
    """Escape a workflow-command message body."""
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(value: str) -> str:
    """Escape a workflow-command property value (``file=``, ``title=`` and so on)."""
    return _escape_data(value).replace(":", "%3A").replace(",", "%2C")


def running_in_github_actions() -> bool:
    """GitHub sets ``GITHUB_ACTIONS=true`` on every hosted and self-hosted runner."""
    return os.environ.get("GITHUB_ACTIONS") == "true"


@dataclass
class Reporter:
    """Collects and emits diagnostics for one command-line invocation.

    The reporter counts errors so entry points can derive their exit status from it, and it
    can append a Markdown block to the job summary page so that a failed job explains itself
    without anyone opening the raw log.
    """

    stream: TextIO = field(default_factory=lambda: sys.stdout)
    github: bool = field(default_factory=running_in_github_actions)
    errors: int = 0
    warnings: int = 0

    def _emit(self, level: str, message: str, title: str | None, file: str | None,
              line: int | None) -> None:
        if self.github:
            props = []
            if file is not None:
                props.append(f"file={_escape_property(file)}")
            if line is not None:
                props.append(f"line={line}")
            if title is not None:
                props.append(f"title={_escape_property(title)}")
            prop_text = (" " + ",".join(props)) if props else ""
            print(f"::{level}{prop_text}::{_escape_data(message)}", file=self.stream)
            return
        # Local, human-oriented rendering in the familiar "path:line: level: message" shape that
        # editors and terminals already know how to hyperlink.
        location = ""
        if file is not None:
            location = f"{file}:{line}: " if line is not None else f"{file}: "
        heading = f"{title}: " if title else ""
        print(f"{location}{level}: {heading}{message}", file=self.stream)

    def error(self, message: str, *, title: str | None = None, file: str | None = None,
              line: int | None = None) -> None:
        """Report a problem that must fail the invocation."""
        self.errors += 1
        self._emit("error", message, title, file, line)

    def warning(self, message: str, *, title: str | None = None, file: str | None = None,
                line: int | None = None) -> None:
        """Report a problem worth attention that does not fail the invocation."""
        self.warnings += 1
        self._emit("warning", message, title, file, line)

    def notice(self, message: str, *, title: str | None = None) -> None:
        """Report purely informational context (for example the computed version)."""
        self._emit("notice", message, title, None, None)

    def summary(self, markdown: str) -> None:
        """Append Markdown to the job summary when running in Actions; print it otherwise."""
        path = os.environ.get("GITHUB_STEP_SUMMARY")
        if self.github and path:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(markdown.rstrip("\n") + "\n\n")
        else:
            print(markdown, file=self.stream)

    @property
    def exit_code(self) -> int:
        """Conventional process status: 0 when no error was reported, 1 otherwise."""
        return 1 if self.errors else 0


def write_github_outputs(values: dict[str, str]) -> None:
    """Expose ``values`` as step outputs via ``$GITHUB_OUTPUT`` (no-op outside Actions).

    Multi-line values use the documented heredoc-style delimiter syntax. The delimiter is chosen so
    that it cannot occur inside the value, which is what prevents output injection.
    """
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            if "\n" in value:
                delimiter = "EOF_RELEASE_TOOLS"
                while delimiter in value:
                    delimiter += "_"
                handle.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")
            else:
                handle.write(f"{key}={value}\n")
