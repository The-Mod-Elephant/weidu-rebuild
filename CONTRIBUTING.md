# Contributing

Security issues follow [SECURITY.md](SECURITY.md), never public issues.

## Development setup

The development shell in `flake.nix` provides the Rust toolchain and every tool used in CI:

```sh
nix develop          # or: cp .envrc.sample .envrc && direnv allow
hk install           # git hooks from hk.pkl (pre-commit and commit-msg)
git config commit.template .gitmessage
```

## Checks

Run before pushing; CI runs the same hooks:

```sh
hk check --all
cargo test --workspace --locked
```

Local results are evidence, not verification: GitHub Actions is the authoritative gate. In the
pull request, record what you ran locally and what you could not run.

## Commit messages

Commits and pull request titles follow
[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/). The commit-msg hook
checks every commit with `hk util check-conventional-commit`; CI checks the pull request title,
which becomes the commit on `main` when squash-merging.

```text
<type>(<optional scope>)<optional !>: <description>
```

| Type | Use for |
| --- | --- |
| `feat` | A new user-facing feature |
| `fix` | A user-facing bug fix |
| `perf` | A performance improvement |
| `revert` | Reverting a previous commit |
| `refactor` | A code change that neither fixes a bug nor adds a feature |
| `docs` | Documentation only |
| `style` | Formatting only |
| `test` | Tests only |
| `build` | Build system, toolchain or dependencies |
| `ci` | CI configuration |
| `chore` | Other maintenance |

Headers are at most 100 characters. A `!` after the type or a `BREAKING CHANGE:` footer marks a
breaking change.

## Continuous integration

| Workflow | Check | Purpose |
| --- | --- | --- |
| `lint.yml` | `pre-commit` | Every hk hook on all files, then the pull request title; on `main` it also refreshes the Nix cache |
| `codeql.yml` | `Analyze (...)` | CodeQL code scanning |
| `tests.yaml` | `build (<os>, <target>, ...)` | `cargo test` on every supported target |
| `build.yaml` | `build (<os>, <target>, ...)`, `build-nix` | Tests and release builds per target, uploaded as artifacts, and `nix build` |
| `release.yaml` | `release` | Started with a `build.yaml` run ID; publishes that run's artifacts as a GitHub release |

Repository admins should make `pre-commit` a required status check in the `main` ruleset.
