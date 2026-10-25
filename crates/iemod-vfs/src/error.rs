//! Error type shared by every operation of the sandboxed filesystem.

use std::io;
use std::path::PathBuf;

use thiserror::Error;

use crate::invalid_path_reason::InvalidPathReason;

/// Everything that can go wrong while accessing a game directory.
///
/// Variants carry the *relative* game path a mod asked for (as typed by the mod author) so that
/// diagnostics point at the offending mod instruction rather than at an internal absolute path.
#[derive(Debug, Error)]
pub enum VfsError {
    /// The requested path is not an acceptable game-relative path (see [`InvalidPathReason`]).
    #[error("invalid game path {path:?}: {reason}")]
    InvalidPath {
        /// The path exactly as it was requested.
        path: String,
        /// Which validation rule rejected it.
        reason: InvalidPathReason,
    },

    /// The game root itself could not be opened.
    #[error("cannot open game directory {path}: {source}")]
    OpenRoot {
        /// The directory the user pointed the tool at.
        path: PathBuf,
        /// The underlying operating-system error.
        #[source]
        source: io::Error,
    },

    /// No entry matches the path, even case-insensitively.
    #[error("{path} does not exist in the game directory")]
    NotFound {
        /// The requested game path.
        path: String,
    },

    /// Several entries differ only by letter case, so the case-insensitive lookup that the
    /// Infinity Engine relies on cannot pick one deterministically.
    #[error("{path} is ambiguous: the game directory contains {candidates:?}")]
    Ambiguous {
        /// The requested game path.
        path: String,
        /// The conflicting on-disk names, sorted.
        candidates: Vec<String>,
    },

    /// An I/O operation inside the game root failed. Escape attempts (`..`, absolute or
    /// escaping symlinks) surface here as `PermissionDenied` from `cap-std`.
    #[error("cannot {operation} {path}: {source}")]
    Io {
        /// A short verb phrase such as "read" or "list the directory".
        operation: &'static str,
        /// The game path being operated on.
        path: String,
        /// The underlying operating-system error.
        #[source]
        source: io::Error,
    },
}
