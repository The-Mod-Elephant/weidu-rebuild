# Release readiness

A release may be published only when every gate below holds. The release flow is described in
[ADR 0002](../adr/0002-git-tags-as-version-source.md): pushing a `vX.Y.Z` tag runs
`.github/workflows/build.yaml`, which starts `.github/workflows/release.yaml`. Gates marked
*automated* make a workflow fail; the others are checked by the maintainer before pushing the
tag.

## Gates

| # | Gate | How it is enforced |
| --- | --- | --- |
| R1 | The release is made from a `vX.Y.Z` tag on a commit of `main`. | *Automated* in part: `build.yaml` runs for tags matching `v[0-9]+.[0-9]+.[0-9]+` only, and `release.yaml` refuses to run on anything but a tag and passes `--verify-tag` to `gh release create`. Maintainer: the tagged commit is on `main`. |
| R2 | `X.Y.Z` follows SemVer 2.0.0 for the changes since the previous tag (or is an explicit `1.0.0` graduation). | Maintainer. |
| R3 | The tag `vX.Y.Z` does not exist yet. | Maintainer: `git ls-remote --tags origin`. |
| R4 | CI (`pre-commit`, `tests`, `build`, CodeQL) is green on the release commit. | Maintainer: check the commit's status on `main` before tagging. |
| R5 | Every target builds without restored caches, and `iemod --version` prints `iemod X.Y.Z`. | *Automated*: tag builds skip the Cargo and Nix caches, and the `Version smoke test` step of `build.yaml` checks the version. |
| R6 | Third-party notices are shipped and every dependency license is accepted. | `cargo deny` checks the licenses (`lint.yml`). **Not met yet**: no notices are generated or shipped. |
| R7 | No open security advisory affects the release without a fix or a documented decision. | Maintainer: Security tab and `cargo deny` results. |
| R8 | `SECURITY.md` and `docs/architecture/THREAT_MODEL.md` describe the shipped behaviour. | Maintainer, during review of the changes being released. |
| R9 | The generated release notes describe the release. | Maintainer: review, and edit if needed, the notes that `gh release create --generate-notes` wrote. |

## Published artifacts

Each release contains one executable per target, named `iemod-<target>` (`iemod-<target>.exe`
for Windows), built by `build.yaml` for the targets in its matrix. Releases have no archives, no
`SHA256SUMS` file and no build-provenance attestations yet (threat-model T11).

## Repository settings the gates rely on

These are configured by a repository admin and cannot be changed from a pull request:

- The `main` ruleset requires pull requests and the `pre-commit` status check.
- Private vulnerability reporting is enabled (SECURITY.md relies on it).
