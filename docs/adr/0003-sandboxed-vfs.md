# ADR 0003: All game-directory access goes through a capability sandbox

- Status: Accepted
- Date: 2026-10-25

## Context

Mods are untrusted. Path traversal, symlink and hard-link tricks, and destructive operations are
the main ways a mod could damage a user's system (threats T1-T4 and T6 in
`docs/architecture/THREAT_MODEL.md`). Games written for Windows also expect case-insensitive file
names, which case-sensitive filesystems do not provide.

## Decision

Create the `iemod-vfs` crate as the only component allowed to access game files:

1. `RelPath` validates every path lexically and portably (no absolute paths, `..`, drive or UNC
   prefixes, `:`, reserved characters or device names, trailing dots or spaces).
2. `GameRoot` opens the game directory once with `cap_std::fs::Dir` and resolves every access
   relative to it, so `cap-std` rejects any resolution that would leave the directory, including
   through symlinks.
3. Lookups map each component case-insensitively (ASCII folding) and fail on ambiguity.
4. Writes are atomic (temporary file, `sync_all`, rename) and there is no delete API.

## Consequences

- Escape attempts fail with typed errors instead of depending on every caller's care.
- Two independent layers (lexical validation and capability resolution) must both fail for an
  escape to succeed.
- Uninstalling will need a dedicated, journaled mechanism that only removes or restores files the
  tool itself installed; it must be designed explicitly rather than by adding a general delete.
- Each lookup currently lists one directory per path component; caching directory listings is a
  planned optimisation for large installs.
