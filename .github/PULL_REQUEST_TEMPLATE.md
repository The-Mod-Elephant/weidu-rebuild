<!-- Title: a Conventional Commit header, e.g. "feat(vfs): add directory listing". -->

## Summary

<!-- What does this change and why? Link issues with "Closes #123". -->

## Verification

Ran locally:

- [ ] `hk check --all`
- [ ] `cargo clippy --workspace --all-targets --locked -- -D warnings`
- [ ] `cargo test --workspace --locked`

Not covered locally (e.g. other operating systems), or "None":

## Checklist

- [ ] `SECURITY.md`, `docs/architecture/THREAT_MODEL.md` and `docs/release/READINESS.md` are updated if a documented boundary changed.
- [ ] New dependencies pass `cargo deny check`.
- [ ] No credentials or machine-specific paths are included.
