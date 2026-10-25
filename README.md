# iemod

> Why? Because we must.

[![lint](https://github.com/The-Mod-Elephant/weidu-rebuild/actions/workflows/lint.yml/badge.svg)](https://github.com/The-Mod-Elephant/weidu-rebuild/actions/workflows/lint.yml)
[![CodeQL](https://github.com/The-Mod-Elephant/weidu-rebuild/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/The-Mod-Elephant/weidu-rebuild/actions/workflows/codeql.yml)
[![License: GPL-3.0](https://img.shields.io/github/license/The-Mod-Elephant/weidu-rebuild)](LICENSE)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://www.conventionalcommits.org/en/v1.0.0/)

A new, safe and fast toolchain for installing and authoring mods for Infinity Engine games.

> [!NOTE]
> **Status: early scaffolding.** `iemod` is a working title.

## Goals

- **Safe by construction.** Mods are untrusted input: they must not be able to read or write
  outside the game directory, delete files, run programs or use the network. See the
  [threat model](docs/architecture/THREAT_MODEL.md).
- **Fast.** Minimal I/O and linear-time pattern matching.
- **Predictable.** One coherent command-line interface with identical behaviour on Windows, macOS
  and Linux.
- **Easy to build.** A standard Cargo workspace and a Nix development shell.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), and [SECURITY.md](SECURITY.md) before reporting a
vulnerability.

## License

[GPL-3.0](LICENSE).
