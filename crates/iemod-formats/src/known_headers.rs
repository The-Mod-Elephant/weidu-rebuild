use crate::header::Header;

/// `chitin.key`: offset 0x0000 `'KEY '`, 0x0004 `'V1  '`.
/// <https://gibberlings3.github.io/iesdp/file_formats/ie_formats/key_v1.htm>
pub const KEY_V1: Header = Header::new(*b"KEY ", *b"V1  ");
