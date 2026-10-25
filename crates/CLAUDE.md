# Instructions for the Rust crates

These rules add to the repository-wide `CLAUDE.md`.

- Crate roles: `iemod-vfs` is the only code that touches game files on disk; `iemod-formats`
  parses bytes it is given and performs no I/O; `iemod-cli` wires them together and owns user
  interaction and exit statuses (`exit_status.rs`). Keep these boundaries.
- Library code returns typed `thiserror` errors and never panics on input: `unwrap`, `expect`,
  `panic!` and slice indexing are linted (`[workspace.lints.clippy]`). Tests may panic.
- Parsing code cites the IESDP page and field offsets it implements, next to the code.
- Every new filesystem capability needs tests for escape attempts (`..`, absolute paths,
  symlinks, hard links) and for case-insensitive behaviour; keep platform-specific tests behind
  `#[cfg(unix)]`/`#[cfg(windows)]` with a runtime precondition check where needed.
- New dependencies must be justified in the pull request, pass `cargo deny check`, and carry a
  license already allowed in `deny.toml`/`about.toml`.
- Packages have no `version` field (git tags are the version source); do not add one.
