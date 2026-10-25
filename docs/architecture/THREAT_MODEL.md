# Threat model

This document defines the security boundaries of the toolchain. Changes that move a boundary
must update it, together with [SECURITY.md](../../SECURITY.md) and
[READINESS.md](../release/READINESS.md) where relevant (CLAUDE.md, "Sources of truth").

## Assets

1. **The user's files outside the game directory**: documents, other programs, system files.
2. **The game installation**: game data must not be corrupted or silently destroyed.
3. **The user's machine and network**: no code execution or network access on behalf of a mod.
4. **Release integrity**: users must be able to trust that a downloaded binary was built from
   this repository by its release workflow.

## Actors and trust

| Actor | Trust |
| --- | --- |
| The user running `iemod` | Trusted. Chooses the game directory explicitly. |
| Mod authors and mod archives | **Untrusted.** Every path, file and instruction a mod contains is attacker-controlled. |
| Files already in the game directory | Untrusted content. Earlier mods may have placed symlinks, hard links or malformed files there. |
| Maintainers, GitHub Actions, crates.io | Trusted, with supply-chain controls described below. |

## Threats and mitigations

| ID | Threat | Mitigation | Status |
| --- | --- | --- | --- |
| T1 | **Path traversal**: a mod writes to `../../home/user/...`, `/etc/...`, `C:\...` or `\\server\share`. | `RelPath` rejects absolute paths, `..` and `.` components, drive and UNC prefixes, and any `:` (`iemod-vfs/src/rel_path.rs`). | Implemented, tested |
| T2 | **Symlink escape**: a link inside the game directory points outside it. | All access is resolved by `cap-std` within one opened directory; paths that would leave it fail with `PermissionDenied`. Links that stay inside keep working. | Implemented, tested on Unix |
| T3 | **Hard-link redirection**: a planted hard link makes a write modify a file elsewhere. | Writes go to a new temporary file that is renamed over the destination, replacing the link instead of writing through it. | Implemented, tested on Unix |
| T4 | **Destructive operations**: a mod deletes or truncates large parts of the disk or the game. | The VFS exposes no delete operation; writes are atomic, so an interrupted install never leaves a half-written file. A backup and uninstall journal is planned. | Partially implemented |
| T5 | **Code execution and network access**: a mod runs a program or downloads a payload. | The mod language (not yet implemented) will have no process-spawning or network primitive. The workspace denies `unsafe` code; exceptions need an explicit, justified opt-in. | Design constraint |
| T6 | **Name aliasing**: different spellings reach the same file (`FOO.ITM` vs `foo.itm`, `name.` vs `name`, `NUL.txt`), causing confusion or overwrites. | Lookups are case-insensitive with explicit ambiguity errors; names Windows cannot represent are rejected on every platform. | Implemented, tested |
| T7 | **Malformed binary files** crash the tool or cause out-of-bounds reads. | Safe Rust only; parsers validate lengths before reading and return typed errors; panicking shortcuts are linted. Fuzzing is planned with the first full format parser. | Implemented for headers |
| T8 | **Regular-expression denial of service** through mod-supplied patterns. | Only linear-time matching (the Rust `regex` crate) will be used; no backtracking engine. | Design constraint |
| T9 | **Terminal injection** through file contents echoed in diagnostics. | Untrusted bytes are escaped before display (e.g. `Header`'s `Display`). | Implemented for headers |
| T10 | **Supply-chain compromise** of dependencies or CI. | `Cargo.lock` with `--locked` builds; `cargo deny` checks RustSec advisories, licenses and sources; Dependabot with a cooldown; actions pinned by SHA; minimal workflow permissions; zizmor and CodeQL scanning. | Implemented |
| T11 | **Tampered release binaries**. | Release builds only in `release.yml`, from scratch without caches, at the verified commit; `SHA256SUMS` and Sigstore-signed build-provenance attestations; optional reviewer approval through the `release` environment. | Implemented |

## Known limitations

- Reads through a hard link that already exists in the game directory return that file's
  contents; the sandbox prevents writes through it, not reads.
- `cap-std` protects path resolution but cannot stop another process from changing the
  directory tree at the same time.
- Symlink and hard-link tests currently run on Unix only. Creating symbolic links on Windows
  requires the `SeCreateSymbolicLinkPrivilege` privilege or Developer Mode (Microsoft,
  `CreateSymbolicLinkW`), so Windows coverage of T2 relies on `cap-std`'s own guarantees until a
  Windows-specific test is added.
