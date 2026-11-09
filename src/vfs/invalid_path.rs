use std::error::Error;
use std::fmt;

use crate::vfs::InvalidPathReason;

/// A path from a mod that is not a valid game-relative path.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InvalidPath {
    pub path: String,
    pub reason: InvalidPathReason,
}

impl fmt::Display for InvalidPath {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // `path` is untrusted: `{:?}` escapes control characters so it cannot drive the
        // terminal (threat T9).
        write!(f, "invalid path {:?}: {}", self.path, self.reason)
    }
}

impl Error for InvalidPath {}
