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
- `scripts/release.py` computes the next version from the commits since the latest reachable
  final tag (policy in CONTRIBUTING.md, "Versioning").
- `CHANGELOG.md` is prepared in an ordinary pull request (`scripts/changelog.py prepare`).
  `release.yml` refuses to tag unless the newest section matches the computed version, then
  creates the tag at exactly the verified commit.
- Release binaries receive the version at compile time through `IEMOD_RELEASE_VERSION`; every
  other build reports `0.0.0-dev`.

## Consequences

- No bot needs write access to `main`, and no secret beyond the workflow token is required.
- Preparing a release is a reviewed change like any other.
- Tools that read `Cargo.toml` see `0.0.0`; the authoritative version is `iemod --version` of a
  release build, or the tag.
