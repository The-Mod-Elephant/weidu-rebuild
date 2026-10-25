//! Headers of the formats the toolchain currently recognises, with their IESDP references.

use crate::header::Header;

/// `chitin.key`, the resource index of every game: IESDP "KEY file format", version V1,
/// header offsets 0x0000 (signature `'KEY '`) and 0x0004 (version `'V1  '`).
/// <https://gibberlings3.github.io/iesdp/file_formats/ie_formats/key_v1.htm>
pub const KEY_V1: Header = Header::new(*b"KEY ", *b"V1  ");
