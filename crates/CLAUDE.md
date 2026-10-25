# Instructions for the Rust crates

These rules add to the repository-wide `CLAUDE.md`.

- `iemod-vfs` is the only code that touches game files; `iemod-formats` parses bytes and does no
  I/O; `iemod-cli` owns user interaction.
- Library code returns typed `thiserror` errors and never panics on input: no `unwrap`,
  `expect` or unchecked indexing on untrusted data (a review rule). Tests may panic.
- The CLI exits with `ExitCode::SUCCESS` or `ExitCode::FAILURE` and prints the error; do not
  invent exit codes.
- Parsing code cites the IESDP page and offsets it implements.
- New filesystem capabilities need tests for escape attempts (`..`, absolute paths, symlinks,
  hard links) and case-insensitive behaviour.
- New dependencies must pass `cargo deny check`.
- Packages have no `version` field; git tags are the version source.
