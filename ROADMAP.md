# Roadmap

This roadmap lists the work that is planned for `iemod`, in the order that has been agreed in
review, and where each piece stands. It describes intent, not commitments: the project is
maintained by volunteers ([SECURITY.md](SECURITY.md)), so no item has a date.

## How this roadmap is maintained

- A pull request that starts, finishes or drops an item updates this file in the same change.
- Every item cites the decision record, threat-model entry or pull request it comes from. Work
  that has no such source is listed under [Open questions](#open-questions), not as a plan.
- The status of each security mitigation lives in the
  [threat model](docs/architecture/THREAT_MODEL.md); this file links to it rather than
  repeating it.

Status values: **Done** (on `main`), **In review** (an open pull request), **Next** (agreed and
ordered, not started), **Needs design** (required, but there is no agreed design yet).

## Foundation

| Item | Status | Source |
| --- | --- | --- |
| Nix development shell, hk hooks, repository hygiene, commit linting and hardened workflows | Done | [#1](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/1)–[#9](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/9), [#16](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/16) |
| Rust as the implementation language | Done | [ADR 0001](docs/adr/0001-rust.md) |
| Git tags as the only version source | Done (decision) | [ADR 0002](docs/adr/0002-git-tags-as-version-source.md) |
| Cargo workspace, workspace lints, `cargo deny` policy and the `iemod` CLI scaffold (`--help`, `--version`) | Done | [#14](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/14) |
| Tests on every supported platform (`tests.yaml`) | Done | [#17](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/17) |
| Release builds and artifacts on every supported platform (`build.yaml`) | In review | [#19](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/19) |
| Dependabot updates with low-risk auto-merge | Merged into the `ci/rust-tests` branch, not yet on `main` | [#11](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/11) |
| git-cliff versioning and changelog, tag-driven `release.yml` and reusable `build.yml` | In review (targets `ci/rust-tests`) | [#12](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/12) |

## Milestones

The order below is the one agreed when
[#10](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/10) was split into one concern per
pull request. Each milestone is its own pull request with its tests inline
([crates/CLAUDE.md](crates/CLAUDE.md)).

### 1. Sandboxed game directory (`iemod-vfs`): Next

The only crate that may touch game files ([ADR 0003](docs/adr/0003-sandboxed-vfs.md)). It
should be built on an existing crate rather than written from scratch
([review](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/18#discussion_r4506602116)):

1. Find an existing crate that provides the sandbox. ADR 0003 already plans to use `cap-std`
   for path resolution. The candidates are measured against these requirements:
   - lexical, portable path validation (threats T1 and T6);
   - every access resolved inside one capability-opened directory (T2);
   - ASCII case-insensitive lookups that fail on ambiguity (T6);
   - atomic writes through a temporary file and rename, and no delete API (T3, T4).
2. Record the choice, its license and its platform support in an ADR that amends ADR 0003. The
   crate must also pass `cargo deny check`.
3. `iemod-vfs` wraps the chosen crate and adds only what it lacks, so all game-directory I/O
   still goes through `iemod-vfs`.

Follow-up: a Windows-specific symlink-escape test. Until one exists, the threat model lists
Windows coverage of T2 as a known limitation.

### 2. Infinity Engine file formats: Next, after milestone 1

- One struct per file type, with sub-structs for its sections, each citing its
  [IESDP](https://gibberlings3.github.io/iesdp/) page and offsets, as requested in
  [this review thread](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/10#discussion_r4471237815).
- Parsers validate every length and offset and return typed errors (T7).
- Untrusted bytes are escaped before they are displayed (T9).
- Fuzzing starts with the first complete format parser (T7).

### 3. `iemod doctor`: Next, after milestones 1 and 2

The first command. The
[#10 split plan](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/10) adds it "once vfs and
formats exist".

## Release track

The first `0.y.z` release can be made once the release workflow
([#12](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/12)) is on `main` and every gate in
[READINESS.md](docs/release/READINESS.md) holds. Until then there are no published binaries.

## Needs design

These items are required by the threat model or the decision records, but there is no agreed
design or order for them yet.

- **Mod language.** No primitive may spawn a process or use the network (T5). Text matching is
  linear-time only (T8).
- **Backup and uninstall journal.** It removes or restores only files that `iemod` installed
  itself, instead of a general delete (T4, [ADR 0003](docs/adr/0003-sandboxed-vfs.md)).
- **Directory-listing cache.** Today each lookup lists one directory per path component; a
  cache would make large installs faster ([ADR 0003](docs/adr/0003-sandboxed-vfs.md)).

## Open questions

- Where the format parsers live: a crate in this workspace, a separately published crate, or an
  existing models crate
  ([review thread](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/10#discussion_r4471237815)).
- The final project name: `iemod` is a working title ([README.md](README.md)).
- What a `1.0.0` release requires. It is not defined yet; the release gates only state that
  `1.0.0` is an explicit graduation (R2 in [READINESS.md](docs/release/READINESS.md)).
