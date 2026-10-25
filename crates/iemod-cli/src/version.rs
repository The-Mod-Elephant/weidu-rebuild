/// Git tags are the only version source, so release builds receive the tag through
/// `IEMOD_RELEASE_VERSION` (set by release.yml); any other build is a development build.
pub const VERSION: &str = match option_env!("IEMOD_RELEASE_VERSION") {
    Some(version) => version,
    None => "0.0.0-dev",
};
