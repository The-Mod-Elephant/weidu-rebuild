, [#23](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/23) |# Roadmap

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
| Cargo workspace, `cargo deny` policy and the `iemod` CLI scaffold (`--help`, `--version`) | Done | [#14](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/14) |
| Tests on every supported platform (`tests.yaml`) | Done | [#17](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/17) |
| Single root package in place of the `crates/` workspace, and release builds and artifacts on every supported platform (`build.yaml`) | Done | [#19](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/19) |
| Tag-driven release: `build.yaml` builds a pushed `vX.Y.Z` tag and starts `release.yaml`, which publishes that run's executables as a GitHub release | Done | [#20](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/20) |
| Dependabot updates with low-risk auto-merge | Not on `main`: #11 was merged into the `ci/rust-tests` branch, which was deleted without being merged | [#11](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/11) |
| git-cliff versioning and changelog | Dropped: #12 was closed unmerged, and #20 provides the release workflow instead | [#12](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/12) |

## Milestones

The order below is the one agreed when
[#10](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/10) was split into one concern per
pull request. Each milestone is its own pull request with its tests inline
([`crates/CLAUDE.md` as of 12dfb72](https://github.com/The-Mod-Elephant/weidu-rebuild/blob/12dfb72/crates/CLAUDE.md),
removed in [#19](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/19)).

### 1. Sandboxed game directory (`vfs` module): Next

The only module that may touch game files (`src/vfs/`,
[ADR 0003](docs/adr/0003-sandboxed-vfs.md)). It should be built on an existing crate rather than
written from scratch
([review](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/18#discussion_r4506602116)):

1. Find an existing crate that provides the sandbox. ADR 0003 already plans to use `cap-std`
   for path resolution. The candidates are measured against these requirements:
   - lexical, portable path validation (threats T1 and T6);
   - every access resolved inside one capability-opened directory (T2);
   - ASCII case-insensitive lookups that fail on ambiguity (T6);
   - atomic writes through a temporary file and rename, and no delete API (T3, T4).
2. Record the choice, its license and its platform support in an ADR that amends ADR 0003. The
   crate must also pass `cargo deny check`.
3. The `vfs` module wraps the chosen crate and adds only what it lacks, so all game-directory
   I/O still goes through it.

| Part | Status | Source |
| --- | --- | --- |
| `RelPath`, the lexical, portable path validation (T1, T6). No candidate crate rejects the names Windows cannot represent on every platform with a typed error, so the module implements it. | In review | [#24](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/24) |

Follow-up: a Windows-specific symlink-escape test. Until one exists, the threat model lists
Windows coverage of T2 as a known limitation.

### 2. Infinity Engine file formats: Next, after milestone 1

- The format types live in one shared crate that other repositories can use too
  ([review](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/18#discussion_r4506605123)).
- One struct per file type, with sub-structs for its sections, each citing its
  [IESDP](https://gibberlings3.github.io/iesdp/) page and offsets, as requested in
  [this review thread](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/10#discussion_r4471237815).
- The structs derive [`zerocopy`](https://docs.rs/zerocopy)'s traits (`FromBytes`, `KnownLayout`,
  `Immutable`, `Unaligned`), so a record is read in place from the file bytes
  ([review](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/18#discussion_r4506602922)).
  Multi-byte fields use its `little_endian` types, and a buffer that is too short is an error,
  not a panic. The crate encapsulates the unsafe code that reading in place needs, and its license
  (`BSD-2-Clause OR Apache-2.0 OR MIT`) is accepted by `deny.toml`.
- Parsers validate every length and offset and return typed errors (T7).
- Untrusted bytes are escaped before they are displayed (T9).
- Fuzzing starts with the first complete format parser (T7).

## Release track

The release flow from [#20](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/20) is on `main`
(see [ADR 0002](docs/adr/0002-git-tags-as-version-source.md)). The first `0.y.z` release can be
made once every gate in [READINESS.md](docs/release/READINESS.md) holds. Until then there are no
tags and no published binaries. Remaining release work:

- Third-party notices are not generated or shipped yet, so gate R6 does not hold.
- `SHA256SUMS`, build-provenance attestations and a `release` environment (threat-model T11).

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

- Where the shared format-types crate lives, and how other repositories get it: a crate in this
  workspace published to crates.io (packages are currently `publish = false`), or a crate in its
  own repository
  ([review](https://github.com/The-Mod-Elephant/weidu-rebuild/pull/18#discussion_r4506605123)).
- The final project name: `iemod` is a working title ([README.md](README.md)).
- What a `1.0.0` release requires. It is not defined yet; the release gates only state that
  `1.0.0` is an explicit graduation (R2 in [READINESS.md](docs/release/READINESS.md)).
