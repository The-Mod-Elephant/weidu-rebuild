#!/usr/bin/env python3
"""Package one release binary with its legal and user documentation into an archive.

Usage:
  package_release.py --binary <path> --target <triple> --version <X.Y.Z> \\
                     --notices <THIRD_PARTY_NOTICES.md> --out-dir <dir>

Produces ``iemod-v<version>-<target>.zip`` for Windows targets and ``.tar.gz`` otherwise,
containing a single top-level directory with the executable, LICENSE, README.md, CHANGELOG.md and
the third-party notices. Archives are deterministic: entries are sorted, owners are zeroed and
every timestamp is the release commit's time taken from ``SOURCE_DATE_EPOCH`` (the
reproducible-builds.org convention), so rebuilding the same commit yields identical bytes.
Only the standard library is used, so the same code runs on every release runner.
"""

from __future__ import annotations

import argparse
import gzip
import io
import os
import sys
import tarfile
import time
import zipfile
from pathlib import Path

from release_tools.semver import SemverError, Version

# Files copied from the repository root into every archive, besides the binary and notices.
DOCUMENTS = ("LICENSE", "README.md", "CHANGELOG.md")
# Placeholder project name (README.md); also the executable's base name.
PROGRAM = "iemod"


def _epoch() -> int:
    value = os.environ.get("SOURCE_DATE_EPOCH")
    if value is None:
        raise SystemExit("error: SOURCE_DATE_EPOCH must be set (the release commit's Unix time)")
    try:
        epoch = int(value)
    except ValueError:
        raise SystemExit(f"error: SOURCE_DATE_EPOCH={value!r} is not an integer") from None
    # ZIP timestamps cannot represent dates before 1980.
    return max(epoch, 315532800)


def entries(binary: Path, notices: Path, root: Path, windows: bool) -> list[tuple[str, Path, int]]:
    """(archive name, source file, Unix mode) for every member, sorted by archive name."""
    executable = PROGRAM + (".exe" if windows else "")
    members = [(executable, binary, 0o755), ("THIRD_PARTY_NOTICES.md", notices, 0o644)]
    members += [(name, root / name, 0o644) for name in DOCUMENTS]
    for _, source, _ in members:
        if not source.is_file():
            raise SystemExit(f"error: {source} does not exist or is not a file")
    return sorted(members)


def write_zip(path: Path, prefix: str, members: list[tuple[str, Path, int]], epoch: int) -> None:
    stamp = time.gmtime(epoch)[:6]
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, source, mode in members:
            info = zipfile.ZipInfo(f"{prefix}/{name}", date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100000 | mode) << 16  # regular file + permission bits
            info.create_system = 3  # "Unix", so the permission bits above are honoured
            archive.writestr(info, source.read_bytes())


def write_tar_gz(path: Path, prefix: str, members: list[tuple[str, Path, int]], epoch: int) -> None:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, source, mode in members:
            data = source.read_bytes()
            info = tarfile.TarInfo(f"{prefix}/{name}")
            info.size, info.mode, info.mtime = len(data), mode, epoch
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(data))
    # mtime=epoch and an empty filename keep the gzip header itself deterministic.
    with open(path, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw,
                                                mtime=epoch) as compressed:
        compressed.write(buffer.getvalue())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--target", required=True, help="Rust target triple")
    parser.add_argument("--version", required=True)
    parser.add_argument("--notices", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    args = parser.parse_args(argv)

    try:
        version = Version.parse(args.version)  # refuses anything that is not strict SemVer
    except SemverError as exc:
        raise SystemExit(f"error: {exc}") from None
    windows = "windows" in args.target
    prefix = f"{PROGRAM}-{version.tag}-{args.target}"
    members = entries(args.binary, args.notices, args.root, windows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    path = args.out_dir / (prefix + (".zip" if windows else ".tar.gz"))
    (write_zip if windows else write_tar_gz)(path, prefix, members, _epoch())
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
