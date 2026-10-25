use thiserror::Error;

use crate::header::Header;

#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum FormatError {
    #[error("truncated data: {needed} bytes are required but only {actual} are present")]
    Truncated { needed: usize, actual: usize },

    #[error("unexpected file header: expected {expected}, found {found}")]
    UnexpectedHeader { expected: Header, found: Header },
}
