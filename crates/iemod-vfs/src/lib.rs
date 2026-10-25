//! Sandboxed access to an Infinity Engine game directory.
//!
//! Mods are untrusted input. This crate is the only component allowed to touch game data on
//! disk (CLAUDE.md, "Product and architecture invariants"), and it guarantees that:
//!
//! * every path is validated lexically by [`RelPath`] before use (no absolute paths, no `..`,
//!   no drive letters, alternate data streams or names Windows cannot represent);
//! * every access is resolved by `cap-std` inside one opened directory, so symlinks cannot
//!   escape the game root;
//! * lookups are case-insensitive, matching how the games behave on Windows;
//! * writes are atomic, and there is no API to delete files.
//!
//! See `docs/adr/0003-sandboxed-vfs.md` for the design rationale.

mod case_resolution;
mod error;
mod game_root;
mod invalid_path_reason;
mod rel_path;

pub use error::VfsError;
pub use game_root::GameRoot;
pub use invalid_path_reason::InvalidPathReason;
pub use rel_path::RelPath;
