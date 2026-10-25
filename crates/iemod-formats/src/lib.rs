//! Parsers for Infinity Engine file formats, following the IESDP file-format reference
//! (<https://gibberlings3.github.io/iesdp/>).
//!
//! Every parser treats its input as untrusted: lengths and offsets are validated before use and
//! malformed data yields a [`FormatError`], never a panic. Only the common file header is
//! implemented so far; full format parsers are future work.

mod format_error;
mod header;
mod known_headers;

pub use format_error::FormatError;
pub use header::Header;
pub use known_headers::KEY_V1;
