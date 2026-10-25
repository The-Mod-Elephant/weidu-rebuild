//! Many IESDP formats start with a 4-byte signature at 0x0000 and a 4-byte version at 0x0004.

use std::fmt;

use crate::format_error::FormatError;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Header {
    pub signature: [u8; 4],
    pub version: [u8; 4],
}

impl Header {
    pub const LEN: usize = 8;

    #[must_use]
    pub const fn new(signature: [u8; 4], version: [u8; 4]) -> Self {
        Self { signature, version }
    }

    /// # Errors
    ///
    /// [`FormatError::Truncated`] when `data` is shorter than [`Header::LEN`].
    pub fn parse(data: &[u8]) -> Result<Self, FormatError> {
        let truncated = || FormatError::Truncated {
            needed: Self::LEN,
            actual: data.len(),
        };
        let (signature, rest) = data.split_first_chunk::<4>().ok_or_else(truncated)?;
        let (version, _) = rest.split_first_chunk::<4>().ok_or_else(truncated)?;
        Ok(Self {
            signature: *signature,
            version: *version,
        })
    }

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
    /// Escapes non-printable bytes so untrusted input cannot inject terminal control sequences.
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
