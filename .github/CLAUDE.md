# Instructions for `.github/`

These rules add to the repository-wide `CLAUDE.md`; they apply to workflows, Dependabot and
templates.

- Pin every action to a full 40-character commit SHA followed by `# vX.Y.Z`. Resolve the SHA from
  the upstream release with `gh api repos/<owner>/<repo>/commits/<tag> --jq .sha`, never from
  memory. Tool versions installed inside jobs (cargo-deny, cargo-about, zizmor, actionlint) are
  pinned explicitly too; Dependabot cannot update them, so bump them deliberately.
- Start every workflow with `permissions: {}` and grant each job only what it uses, with a
  trailing comment per permission explaining why (zizmor's pedantic persona checks this).
- Always `persist-credentials: false` on checkout. Pass untrusted event data (titles, branch
  names) through `env:` and quote it in scripts; never interpolate `${{ }}` into `run:` bodies.
- Do not use `pull_request_target` or `workflow_run` without a written threat analysis.
- Failures must explain themselves: emit `::error file=...,line=...,title=...::` annotations or a
  job summary naming the cause and the fix, not just a non-zero exit.
- Protect CI minutes: route new jobs through the `changes` job in `ci.yml` (add paths to
  `scripts/detect_changes.py`), skip with `if:` rather than workflow-level `paths:` (which would
  leave required checks pending), and add every new job to the `needs` of `CI gate`.
- Validate locally before pushing: `actionlint` and `zizmor --persona=pedantic .github` must both
  report nothing (see CONTRIBUTING.md for installation).
