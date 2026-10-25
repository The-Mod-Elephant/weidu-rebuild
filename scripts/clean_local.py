#!/usr/bin/env python3
"""Remove regenerable local build output from the working tree.

Usage: clean_local.py [--dry-run]

Only the fixed, known-regenerable locations below are removed, and only when they resolve to a
path inside the repository root; symlinks are unlinked, never followed, so a link pointing
elsewhere cannot cause anything outside the checkout to be deleted. Tracked files are never
touched because none of these locations is tracked (see .gitignore).
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from release_tools.git import Git, GitError

# Top-level directories produced by `cargo` and by local release packaging dry runs.
TOP_LEVEL = ("target", "dist")
# Directory names produced anywhere by the Python interpreter.
ANYWHERE = ("__pycache__",)


def candidates(root: Path) -> list[Path]:
    """Every existing path that would be removed, in a stable order."""
    found = [root / name for name in TOP_LEVEL if (root / name).exists() or (root / name).is_symlink()]
    # os.walk with followlinks=False (its default, spelled out) never descends through symlinked
    # directories, so the search cannot wander outside the checkout. .git and the top-level
    # output directories are pruned: they are either off-limits or removed wholesale anyway.
    for current, dirnames, _ in os.walk(root, followlinks=False):
        here = Path(current)
        if here == root:
            dirnames[:] = [d for d in dirnames if d != ".git" and d not in TOP_LEVEL]
        for name in sorted(dirnames):
            if name in ANYWHERE:
                found.append(here / name)
        dirnames[:] = sorted(d for d in dirnames if d not in ANYWHERE)
    return found


def remove(path: Path, root: Path) -> None:
    """Delete one candidate after re-checking that it lives inside ``root``."""
    if path.is_symlink():
        path.unlink()  # removes the link itself, never its target
        return
    resolved = path.resolve()
    if resolved == root or root not in resolved.parents:
        raise RuntimeError(f"refusing to delete {path}: it resolves outside {root}")
    shutil.rmtree(resolved)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="only list what would be removed")
    args = parser.parse_args(argv)
    try:
        root = Git(Path.cwd()).toplevel().resolve()
    except GitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    paths = candidates(root)
    for path in paths:
        print(("would remove " if args.dry_run else "removing ") + str(path.relative_to(root)))
        if not args.dry_run:
            remove(path, root)
    if not paths:
        print("nothing to clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
