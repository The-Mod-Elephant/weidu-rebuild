pub const VERSION: &str = match option_env!("IEMOD_RELEASE_VERSION") {
    Some(version) => version,
    None => "0.0.0-dev",
};
