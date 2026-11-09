//! The only module allowed to access game files (ADR 0003).

mod invalid_path;
mod invalid_path_reason;
mod rel_path;

pub use invalid_path::InvalidPath;
pub use invalid_path_reason::InvalidPathReason;
#[expect(
    unused_imports,
    reason = "no code outside the vfs module uses RelPath yet"
)]
pub use rel_path::RelPath;
