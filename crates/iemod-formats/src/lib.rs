//! Parsers for Infinity Engine file formats (<https://gibberlings3.github.io/iesdp/>).
//! Input is untrusted: malformed data yields a [`FormatError`], never a panic.

mod format_error;
mod header;
mod known_headers;

pub use format_error::FormatError;
pub use header::Header;
pub use known_headers::KEY_V1;
