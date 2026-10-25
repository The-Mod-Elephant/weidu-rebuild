# Instructions for `.github/`

These rules add to the repository-wide `CLAUDE.md`.

- Pin every action to a full commit SHA with a `# vX.Y.Z` comment, resolved with
  `gh api repos/<owner>/<repo>/commits/<tag> --jq .sha`, never from memory.
- Tools used by jobs come from the Nix shell (`nix develop -c ...`), not ad-hoc installs.
- Start every workflow with `permissions: {}` and grant each job only what it needs, with a short
  comment per permission (zizmor's pedantic persona checks this).
- Always `persist-credentials: false` on checkout. Pass untrusted event data through `env:`;
  never interpolate `${{ }}` into `run:` bodies.
- Do not use `pull_request_target` or `workflow_run`.
- Failures must name their cause, e.g. with `::error title=...::` annotations.
- Skip unaffected jobs with `if:` rather than workflow-level `paths:`, which would leave required
  checks pending; add every CI job to the `needs` of `CI gate`.
- `hk check --all` (actionlint and zizmor included) must pass before pushing.
