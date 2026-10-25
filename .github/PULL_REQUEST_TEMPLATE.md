<!--
Title: a Conventional Commit header, e.g. "feat(vfs): add directory listing". It becomes the
squash-merge commit on main and is checked by the "Conventional commits" job.
-->

## Summary

<!-- What does this change and why? Link issues with "Closes #123". -->

## Changes

<!-- Bullet list of the notable changes, grouped by area. -->

-

## Verification

Local runs (evidence, not verification; see CONTRIBUTING.md#verification):

- [ ] `cargo fmt --all --check`
- [ ] `cargo clippy --workspace --all-targets --locked -- -D warnings`
- [ ] `cargo test --workspace --locked`
- [ ] `python3 -m unittest discover --start-directory scripts/tests --top-level-directory scripts`
- [ ] `python3 scripts/changelog.py validate`

Coverage that was unavailable locally or intentionally skipped:

<!-- e.g. "Windows path behaviour: only covered by the CI Windows job". Write "None" if none. -->

## Checklist

- [ ] `CHANGELOG.md` has an entry under `[Unreleased]` for every user-visible change.
- [ ] `SECURITY.md`, `docs/architecture/THREAT_MODEL.md` and `docs/release/READINESS.md` are updated if a documented boundary changed.
- [ ] Third-party notices policy is respected if dependencies were added (`deny.toml`, `about.toml`).
- [ ] No credentials, signing material or machine-specific paths are included.
