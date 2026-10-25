//! Sandboxed access to an Infinity Engine game directory; see `docs/adr/0003-sandboxed-vfs.md`.

mod case_resolution;
mod error;
mod game_root;
mod invalid_path_reason;
mod rel_path;

pub use error::VfsError;
pub use game_root::GameRoot;
pub use invalid_path_reason::InvalidPathReason;
pub use rel_path::RelPath;
