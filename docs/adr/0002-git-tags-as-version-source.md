# ADR 0002: Git tags are the only version source

- Status: Accepted
- Date: 2026-10-25

## Context

Versions must follow SemVer 2.0.0, be computed automatically from Conventional Commits, and stay
consistent with `CHANGELOG.md`. A `VERSION` file or a `version` field in Cargo manifests would be
a second source that can drift from the tags, and keeping it updated would require automation to
push commits to the protected `main` branch.

## Decision

- Release tags `vX.Y.Z` are the single source of truth. There is no `VERSION` file, and Cargo
  packages omit `version` (allowed since Cargo 1.75; such packages also cannot be published by
  accident).
- git-cliff (`cliff.toml`) computes the next version from the Conventional Commits since the
  latest final tag. In 0.y.z, breaking changes bump the minor version; leaving 0.x is an
  explicit `--bump major`.
- `release.yml` generates `CHANGELOG.md` and the release notes from the same commits at release
  time; the changelog ships in the release archives and is not committed. It then creates the
  tag at exactly the planned commit.
- Release binaries receive the version at compile time through `IEMOD_RELEASE_VERSION`; every
  other build reports `0.0.0-dev`.

## Consequences

- No bot needs write access to `main`, and no secret beyond the workflow token is required.
- Releasing is a single workflow run; there is no version-bump or changelog commit to review.
- Tools that read `Cargo.toml` see `0.0.0`; the authoritative version is `iemod --version` of a
  release build, or the tag.
