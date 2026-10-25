# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Versions are git tags; see CONTRIBUTING.md for how releases are prepared.

## [Unreleased]

### Added

- `iemod doctor --game <DIR>` checks that a directory is an Infinity Engine game installation by
  locating `chitin.key` case-insensitively and validating its KEY V1 header, with documented exit
  statuses (0 success, 1 check failed, 2 usage error, 3 access failed).
- Sandboxed game-directory access (`iemod-vfs`): portable path validation, confinement to the
  game root (no `..`, absolute paths or escaping symlinks), case-insensitive lookups with
  ambiguity detection, atomic writes, and no delete operation.
- Infinity Engine file-header parsing (`iemod-formats`) with typed errors for truncated or
  unexpected data.
- Release archives for Linux (x86_64, aarch64), Windows (x86_64) and macOS (x86_64, aarch64)
  with third-party notices, `SHA256SUMS` and signed build-provenance attestations.

[Unreleased]: https://github.com/The-Mod-Elephant/weidu-rebuild/commits/HEAD
