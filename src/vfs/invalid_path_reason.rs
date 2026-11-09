use std::fmt;

/// The first rule a game-relative path violates.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InvalidPathReason {
    Empty,
    /// Starts with `/` or `\`, which includes UNC and `\\?\` or `\\.\` prefixes.
    Absolute,
    EmptyComponent,
    CurrentDirComponent,
    ParentDirComponent,
    /// A drive prefix (`C:`) or an alternate data stream (`file:stream`).
    Colon,
    ReservedCharacter(char),
    ControlCharacter(u32),
    TrailingDotOrSpace,
    ReservedName(String),
    /// Length of the component in UTF-8 bytes.
    ComponentTooLong(usize),
}

impl fmt::Display for InvalidPathReason {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Empty => f.write_str("the path is empty"),
            Self::Absolute => f.write_str("the path is absolute"),
            Self::EmptyComponent => f.write_str("the path has an empty component"),
            Self::CurrentDirComponent => f.write_str("the path has a `.` component"),
            Self::ParentDirComponent => f.write_str("the path has a `..` component"),
            Self::Colon => {
                f.write_str("the path has a `:` (drive prefix or alternate data stream)")
            }
            Self::ReservedCharacter(c) => write!(f, "the path has the reserved character {c:?}"),
            Self::ControlCharacter(code) => {
                write!(f, "the path has the control character U+{code:04X}")
            }
            Self::TrailingDotOrSpace => f.write_str("a path component ends with a dot or a space"),
            Self::ReservedName(name) => write!(f, "a path component is the device name {name}"),
            Self::ComponentTooLong(len) => {
                write!(
                    f,
                    "a path component is {len} bytes long, over the limit of 255"
                )
            }
        }
    }
}
