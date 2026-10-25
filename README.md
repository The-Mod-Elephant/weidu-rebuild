# iemod

> Why? Because we must.

[![CI](https://github.com/The-Mod-Elephant/weidu-rebuild/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/The-Mod-Elephant/weidu-rebuild/actions/workflows/ci.yml)
[![CodeQL](https://github.com/The-Mod-Elephant/weidu-rebuild/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/The-Mod-Elephant/weidu-rebuild/actions/workflows/codeql.yml)
[![Latest release](https://img.shields.io/github/v/release/The-Mod-Elephant/weidu-rebuild?sort=semver&display_name=tag)](https://github.com/The-Mod-Elephant/weidu-rebuild/releases)
[![License: GPL-3.0](https://img.shields.io/github/license/The-Mod-Elephant/weidu-rebuild)](LICENSE)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://www.conventionalcommits.org/en/v1.0.0/)
[![Keep a Changelog](https://img.shields.io/badge/changelog-Keep%20a%20Changelog%201.1.0-%23E05735)](CHANGELOG.md)

A new, safe and fast toolchain for installing and authoring mods for Infinity Engine games.

> [!NOTE]
> **Status: early scaffolding.** The repository currently contains the project infrastructure,
> the sandboxed filesystem layer, a file-header parser and a first `doctor` command. The mod
> language does not exist yet. `iemod` is a **working title** and will be renamed once the
> project has a name.

## Goals

- **Safe by construction.** Mods are untrusted input. All game-directory access goes through a
  capability-based sandbox that cannot reach outside the game folder, cannot follow symlinks out
  of it, and has no way to delete files. Mods cannot run programs or use the network. See the
  [threat model](docs/architecture/THREAT_MODEL.md).
- **Fast.** Minimal I/O, case-insensitive lookups without repeated directory scans (planned),
  and linear-time pattern matching (the Rust `regex` engine) instead of backtracking.
- **Predictable.** One command-line interface with documented exit statuses, typed error
  messages, and identical behaviour on Windows, macOS and Linux.
- **Easy to build and audit.** A standard Cargo workspace, a pinned toolchain, and CI that
  explains every failure.

## Installation

Prebuilt archives for Windows, macOS and Linux are attached to each
[GitHub Release](https://github.com/The-Mod-Elephant/weidu-rebuild/releases), with `SHA256SUMS`
and signed build-provenance attestations. Verify a download with the GitHub CLI:

```sh
gh attestation verify iemod-vX.Y.Z-<target>.tar.gz --repo The-Mod-Elephant/weidu-rebuild
```

To build from source you need [rustup](https://rustup.rs/); the pinned toolchain in
`rust-toolchain.toml` is installed automatically:

```sh
cargo build --release --locked
./target/release/iemod --help
```

## Usage

```sh
# Check that a directory is an Infinity Engine game installation.
iemod doctor --game "/path/to/game"
```

| Exit status | Meaning |
| --- | --- |
| `0` | Success. |
| `1` | The command ran, but a check failed (for example, the directory is not a game). |
| `2` | Invalid command-line usage. |
| `3` | The data could not be accessed (missing directory, permissions, I/O error). |

## Repository layout

| Path | Contents |
| --- | --- |
| `crates/iemod-cli` | The `iemod` executable: argument parsing, commands, exit statuses. |
| `crates/iemod-vfs` | Sandboxed, case-insensitive game-directory access. |
| `crates/iemod-formats` | Parsers for Infinity Engine file formats ([IESDP](https://gibberlings3.github.io/iesdp/)). |
| `scripts/` | Release, changelog and commit-message tooling (Python standard library only). |
| `docs/` | Architecture decisions, threat model and release gates. |
| `.github/` | CI, release and Dependabot automation; issue and pull request templates. |

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup,
commit conventions and release process, and [SECURITY.md](SECURITY.md) before reporting a
vulnerability.

## License

Licensed under the GNU General Public License version 3; see [LICENSE](LICENSE). Release archives
include the notices of all third-party dependencies (`THIRD_PARTY_NOTICES.md`).
