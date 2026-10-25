//! The 8-byte signature/version header that starts Infinity Engine resource files.
//!
//! Many formats documented by IESDP (<https://gibberlings3.github.io/iesdp/>) begin with a
//! 4-byte character-array signature at offset 0x0000 followed by a 4-byte character-array
//! version at offset 0x0004, padded with spaces. For example, the KEY V1 header is `'KEY '`
//! followed by `'V1  '`. Each recognised format cites its own IESDP page in `known_headers`.

use std::fmt;

use crate::format_error::FormatError;

/// A file's signature and version fields, compared byte for byte.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Header {
    /// Offset 0x0000, e.g. `*b"KEY "`.
    pub signature: [u8; 4],
    /// Offset 0x0004, e.g. `*b"V1  "`.
    pub version: [u8; 4],
}

impl Header {
    /// Size of the header in bytes.
    pub const LEN: usize = 8;

    /// Build a header from its two fields.
    #[must_use]
    pub const fn new(signature: [u8; 4], version: [u8; 4]) -> Self {
        Self { signature, version }
    }

    /// Read the header from the start of `data`.
    ///
    /// # Errors
    ///
    /// [`FormatError::Truncated`] when `data` is shorter than [`Header::LEN`].
    pub fn parse(data: &[u8]) -> Result<Self, FormatError> {
        let truncated = || FormatError::Truncated {
            needed: Self::LEN,
            actual: data.len(),
        };
        // `split_first_chunk` performs the bounds check and the slice-to-array conversion in one
        // step, so no indexing that could panic is involved.
        let (signature, rest) = data.split_first_chunk::<4>().ok_or_else(truncated)?;
        let (version, _) = rest.split_first_chunk::<4>().ok_or_else(truncated)?;
        Ok(Self {
            signature: *signature,
            version: *version,
        })
    }

    /// Parse the header of `data` and require it to equal `self`.
    ///
    /// # Errors
    ///
    /// [`FormatError::Truncated`] or [`FormatError::UnexpectedHeader`].
    pub fn expect_in(self, data: &[u8]) -> Result<(), FormatError> {
        let found = Self::parse(data)?;
        if found == self {
            Ok(())
        } else {
            Err(FormatError::UnexpectedHeader {
                expected: self,
                found,
            })
        }
    }
}

impl fmt::Display for Header {
    /// Renders as `"KEY " "V1  "`; bytes outside printable ASCII appear as `\xNN` escapes so
    /// that garbage input can never inject terminal control sequences into diagnostics.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "\"{}\" \"{}\"",
            self.signature.escape_ascii(),
            self.version.escape_ascii()
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::known_headers::KEY_V1;

    #[test]
    fn parses_and_matches() {
        assert_eq!(Header::parse(b"KEY V1  trailing").unwrap(), KEY_V1);
        assert!(KEY_V1.expect_in(b"KEY V1  ").is_ok());
    }

    #[test]
    fn rejects_short_input() {
        for len in 0..Header::LEN {
            assert_eq!(
                Header::parse(&b"KEY V1  "[..len]),
                Err(FormatError::Truncated {
                    needed: 8,
                    actual: len
                })
            );
        }
    }

    #[test]
    fn reports_unexpected_header_safely() {
        let error = KEY_V1.expect_in(b"BIFFV1  ").unwrap_err();
        assert_eq!(
            error.to_string(),
            "unexpected file header: expected \"KEY \" \"V1  \", found \"BIFF\" \"V1  \""
        );
        let garbage = Header::parse(b"\x1b[2J\x00\xff\n ").unwrap();
        assert_eq!(garbage.to_string(), "\"\\x1b[2J\" \"\\x00\\xff\\n \"");
    }
}
