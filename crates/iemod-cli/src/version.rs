//! The version string reported by `iemod --version`.
//!
//! Git tags are the only version source (CLAUDE.md, "Sources of truth"), so the manifest carries
//! no version. `.github/workflows/release.yml` exports `IEMOD_RELEASE_VERSION` (the tag without
//! its `v`) while compiling release binaries; every other build reports a development version,
//! which makes an unofficial binary impossible to mistake for a release.

/// `IEMOD_RELEASE_VERSION` captured at compile time, or the development marker.
pub const VERSION: &str = match option_env!("IEMOD_RELEASE_VERSION") {
    Some(version) => version,
    None => "0.0.0-dev",
};
