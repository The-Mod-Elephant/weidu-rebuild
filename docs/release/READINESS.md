# Release readiness

A release may be published only when every gate below holds. Gates marked *automated* are
enforced by `.github/workflows/release.yml` (which refuses to publish otherwise); the others are
checked by the maintainer who starts the workflow.

## Gates

| # | Gate | How it is enforced |
| --- | --- | --- |
| R1 | The release is made from `main`. | *Automated*: the `plan` job only runs for `refs/heads/main`. |
| R2 | The version is the one git-cliff computes from the Conventional Commits since the last tag (or an explicit `major` bump to leave 0.x). | *Automated*: `git cliff --bumped-version` in the `plan` job. |
| R3 | At least one commit since the last tag requires a release. | *Automated*: the `plan` job refuses when the computed tag already exists. |
| R4 | The tag `vX.Y.Z` does not exist yet. | *Automated*: checked when planning and again just before publishing. |
| R5 | CI (`CI gate`, `Conventional commits`, CodeQL) is green on the release commit. | Maintainer: check the commit's status on `main` before starting. |
| R6 | Every target builds with `--locked` from a clean state and `iemod --version` prints the release version. | *Automated*: `build` matrix smoke test. |
| R7 | Third-party notices are generated and every dependency license is accepted. | *Automated*: `cargo about generate` in the `notices` job. |
| R8 | A dry run (`dry_run: true`) of the same commit succeeded. | Maintainer. |
| R9 | No open security advisory affects the release without a fix or a documented decision. | Maintainer: Security tab and `cargo deny` results. |
| R10 | `SECURITY.md` and `docs/architecture/THREAT_MODEL.md` describe the shipped behaviour. | Maintainer, during review of the changes being released. |

## Published artifacts

Each release contains one archive per target (`iemod-vX.Y.Z-<target>.tar.gz`, or `.zip` for
Windows) holding the executable, `LICENSE`, `README.md`, `CHANGELOG.md` and
`THIRD_PARTY_NOTICES.md`; a `SHA256SUMS` file; and build-provenance attestations, which users can
check with `gh attestation verify <archive> --repo <owner>/<repo>`.

## Repository settings the gates rely on

These are configured by a repository admin and cannot be changed from a pull request:

- The `main` ruleset requires pull requests, linear history, and the `CI gate` and
  `Conventional commits` status checks.
- The `release` environment exists and, ideally, requires a reviewer.
- Private vulnerability reporting is enabled (SECURITY.md relies on it).
