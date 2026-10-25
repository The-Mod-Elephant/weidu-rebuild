//! Error type for parsing Infinity Engine binary formats.

use thiserror::Error;

use crate::header::Header;

/// A malformed or unexpected binary resource. Parsers return this instead of panicking, because
/// every resource may come from an untrusted mod (CLAUDE.md, "Product and architecture
/// invariants").
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum FormatError {
    /// The input ends before a structure of the required size.
    #[error("truncated data: {needed} bytes are required but only {actual} are present")]
    Truncated {
        /// Bytes required by the structure being read.
        needed: usize,
        /// Bytes actually available.
        actual: usize,
    },

    /// The signature/version pair is not the one the caller expects.
    #[error("unexpected file header: expected {expected}, found {found}")]
    UnexpectedHeader {
        /// The header the caller requires.
        expected: Header,
        /// The header actually present.
        found: Header,
    },
}
