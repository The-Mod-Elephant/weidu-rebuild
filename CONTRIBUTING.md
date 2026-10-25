# Contributing

Thank you for helping. This guide covers the development setup, the checks every change must
pass, and how commits, versions, changelog entries and releases work. Security issues follow
[SECURITY.md](SECURITY.md), never public issues.

## Development setup

| Tool | Version | Notes |
| --- | --- | --- |
| [rustup](https://rustup.rs/) | any | Installs the toolchain pinned in `rust-toolchain.toml` (with `rustfmt` and `clippy`) on first use. |
| A C toolchain | any | The Rust linker driver: Visual Studio Build Tools on Windows, Xcode Command Line Tools on macOS, `build-essential` (Debian/Ubuntu) on Linux. |
| Python | 3.11 or newer | Runs `scripts/`; standard library only, no packages to install. |
| git | any recent | Used by the release and commit tooling. |

Optional:

- **Nix.** `nix develop` (or `direnv allow` after copying `.envrc.sample` to `.envrc`) provides
  the development shell defined in `flake.nix`, including [hk](https://hk.jdx.dev/) for the git
  hooks configured in `hk.pkl` (`hk install`).
- **Workflow linters.** [actionlint](https://github.com/rhysd/actionlint) and
  [zizmor](https://docs.zizmor.sh/) when you touch `.github/`.
- **Dependency tools.** `cargo install --locked cargo-deny` and
  `cargo install --locked --features cli cargo-about` when you change dependencies.

Enable the commit message template once per clone:

```sh
git config commit.template .gitmessage
```

## Verification

The local machine runs the inner loop; GitHub Actions is the authoritative gate. Local results
are evidence, not verification, because local tools can differ from the pinned CI toolchain.
Run the checks relevant to your change before pushing:

```sh
# Rust
cargo fmt --all --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo test --workspace --locked
cargo deny --locked check                      # when dependencies change

# Python tooling, commit template and changelog
python3 -m unittest discover --start-directory scripts/tests --top-level-directory scripts
python3 scripts/changelog.py validate

# Workflows (when .github/ changes)
actionlint
zizmor --persona=pedantic .github
```

`python3 scripts/clean_local.py` removes regenerable build output (`target/`, `dist/`,
`__pycache__/`); add `--dry-run` to preview. In the pull request, record what you ran locally and
list any coverage you could not run (the template has a section for it).

## Code guidelines

- Follow the repository rules in [CLAUDE.md](CLAUDE.md) and the crate rules in
  [crates/CLAUDE.md](crates/CLAUDE.md): one responsibility per file, files under about 500 lines,
  and comments that explain intent, invariants and sources rather than restating code.
- All game-directory access goes through `iemod-vfs`. Library code returns typed errors and never
  panics on input.
- Binary-format code cites the [IESDP](https://gibberlings3.github.io/iesdp/) page it implements.

## Commit messages

Commits follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```text
<type>(<optional scope>)<optional !>: <description>

<optional body>

<optional footers, e.g. BREAKING CHANGE: ..., Refs: #123>
```

House rules: the type must be one of the table below (lowercase), the scope is a lowercase noun
(`vfs`, `cli`, `formats`, `release`, `ci`, `deps` ...), the header is at most 100 characters,
and reverts use `revert: <original header>` with `Refs: <sha>` in the body. The "Conventional
commits" CI job checks every commit and the pull request title (the title becomes the commit on
`main` when squash-merging). Dependabot pull requests are exempt.

| Type | Use for | Release bump |
| --- | --- | --- |
| `feat` | A new user-facing feature | minor |
| `fix` | A user-facing bug fix | patch |
| `perf` | A change that improves performance | patch |
| `revert` | Reverts a previous commit | patch |
| `refactor` | A code change that neither fixes a bug nor adds a feature | none |
| `docs` | Documentation only changes | none |
| `style` | Formatting changes that do not affect meaning | none |
| `test` | Adding or correcting tests | none |
| `build` | Build system, toolchain or dependency changes | none |
| `ci` | CI configuration and workflow changes | none |
| `chore` | Maintenance that does not touch shipped code | none |

A `!` after the type/scope or a `BREAKING CHANGE:` footer marks a breaking change. The single
source of this table is `scripts/release_tools/commit_types.py`; a unit test keeps `.gitmessage`
in sync, and this table must be updated with it.

## Versioning

Versions follow [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html), and **git tags
named `vX.Y.Z` are the only version source**: there is no `VERSION` file and Cargo manifests have
no `version` field. The next version is computed from the commits since the latest tag:

- `1.0.0` and later: breaking change -> major, `feat` -> minor, `fix`/`perf`/`revert` -> patch.
- `0.y.z` (initial development, SemVer item 4): breaking change -> minor, `feat` -> minor,
  `fix`/`perf`/`revert` -> patch. Moving to `1.0.0` is an explicit decision, made by preparing a
  `## [1.0.0]` changelog section.
- The first release is `0.1.0`, as the SemVer FAQ suggests.
- Commits that bump nothing (`docs`, `ci`, ...) do not justify a release on their own.

`python3 scripts/release.py plan` prints the computed version and the commits behind it.

## Changelog

[CHANGELOG.md](CHANGELOG.md) follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).
Add user-visible changes under `## [Unreleased]`, grouped as `### Added`, `Changed`,
`Deprecated`, `Removed`, `Fixed` or `Security`. Do not edit the link definitions at the bottom by
hand: `python3 scripts/changelog.py fix-links` regenerates them, and CI validates the structure,
ordering, links and the correspondence between sections and tags.

## Releasing

Releases are published **only** by `.github/workflows/release.yml`; never tag or publish by hand.

1. Open a pull request that runs `python3 scripts/changelog.py prepare` (it moves the
   `[Unreleased]` entries into `## [X.Y.Z] - YYYY-MM-DD` using the computed version), titled
   `docs(changelog): prepare vX.Y.Z`, and merge it.
2. In the Actions tab, run **Release** on `main` with `dry_run` enabled. It verifies that the
   prepared section matches the computed version, then builds and smoke-tests all platforms.
3. Run it again with `dry_run` disabled. After approval in the `release` environment (if
   configured), it creates the `vX.Y.Z` tag at the verified commit and publishes the GitHub
   Release with archives, `SHA256SUMS` and provenance attestations.

The gates are listed in [docs/release/READINESS.md](docs/release/READINESS.md).

## Continuous integration

| Workflow | Job (status check) | Runs when |
| --- | --- | --- |
| `ci.yml` | `Detect changes` | always; decides which jobs below are needed |
| `ci.yml` | `Rust formatting`, `Rust tests (<os>)` | Rust files changed; Linux and Windows on pull requests, plus macOS on `main` |
| `ci.yml` | `Dependency policy (cargo-deny)` | Rust files changed, and weekly |
| `ci.yml` | `Python scripts and changelog` | `scripts/`, `CHANGELOG.md` or `.gitmessage` changed |
| `ci.yml` | `Workflow lint (actionlint, zizmor)` | `.github/` automation changed |
| `ci.yml` | **`CI gate`** | always; fails if any job above failed |
| `commits.yml` | **`Conventional commits`** | every pull request except Dependabot's |
| `codeql.yml` | `Analyze (actions/python/rust)` | pull requests, `main`, weekly |

Repository admins should make **`CI gate`** and **`Conventional commits`** required status
checks in the `main` ruleset. Requiring the gate rather than individual jobs means jobs can be
added or skipped without editing the ruleset.

### Dependabot

Dependabot proposes weekly updates for Cargo crates, GitHub Actions and the Rust toolchain, and
monthly updates for `flake.lock`. `dependabot-automerge.yml` enables auto-merge only for low-risk
updates (Actions patch/minor, Cargo patch, toolchain patch), and only if `CI gate` is a required
check, so GitHub merges them after CI passes. Everything else needs a human review. If the job
reports that the token is read-only, Dependabot-triggered workflows on this repository do not
receive write permissions; the updates then simply wait for a manual merge.
