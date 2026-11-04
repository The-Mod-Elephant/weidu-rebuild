# Instructions for the Rust crates

These rules add to the repository-wide `CLAUDE.md`.

- Each crate lives in `crates/<name>` and inherits `[lints] workspace = true`.
- `iemod-cli` owns user interaction. It exits with `ExitCode::SUCCESS` or `ExitCode::FAILURE`
  and prints the error; clap's own usage errors keep clap's exit code. Do not invent exit codes.
- Library code returns typed `thiserror` errors and never panics on input: no `unwrap`,
  `expect` or unchecked indexing on untrusted data (a review rule). Tests may panic.
- Unit tests live next to the code in a `#[cfg(test)] mod tests`.
- New dependencies must pass `cargo deny check`.
- Packages have no `version` field; git tags are the version source.
