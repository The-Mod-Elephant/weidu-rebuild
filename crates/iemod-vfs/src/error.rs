use std::io;
use std::path::PathBuf;

use thiserror::Error;

use crate::invalid_path_reason::InvalidPathReason;

/// Errors carry the game path as the mod wrote it, so diagnostics point at the mod.
#[derive(Debug, Error)]
pub enum VfsError {
    #[error("invalid game path {path:?}: {reason}")]
    InvalidPath {
        path: String,
        reason: InvalidPathReason,
    },

    #[error("cannot open game directory {path}: {source}")]
    OpenRoot {
        path: PathBuf,
        #[source]
        source: io::Error,
    },

    #[error("{path} does not exist in the game directory")]
    NotFound { path: String },

    /// Several entries differ only by case, so a case-insensitive lookup cannot pick one.
    #[error("{path} is ambiguous: the game directory contains {candidates:?}")]
    Ambiguous {
        path: String,
        candidates: Vec<String>,
    },

    /// Escape attempts (`..`, absolute or escaping symlinks) arrive here as `PermissionDenied`
    /// from `cap-std`.
    #[error("cannot {operation} {path}: {source}")]
    Io {
        operation: &'static str,
        path: String,
        #[source]
        source: io::Error,
    },
}
