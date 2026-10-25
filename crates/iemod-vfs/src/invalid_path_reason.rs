use std::fmt;

/// Why `RelPath::parse` rejected a path.
///
/// Names Windows cannot represent are rejected on every platform so that a mod behaves the same
/// everywhere. Windows rules: <https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file>.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InvalidPathReason {
    Empty,
    Absolute,
    EmptyComponent,
    CurrentDirComponent,
    ParentDirComponent,
    /// Drive designators (`C:`) and NTFS alternate data streams (`file:stream`).
    Colon,
    ReservedCharacter(char),
    ControlCharacter(u32),
    /// Windows silently strips trailing spaces and periods, so such names would alias others.
    TrailingDotOrSpace,
    ReservedName(String),
    /// 255 bytes: the ext4 limit, and within NTFS's 255 UTF-16 units.
    ComponentTooLong(usize),
}

impl fmt::Display for InvalidPathReason {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Empty => f.write_str("the path is empty"),
            Self::Absolute => f.write_str("absolute paths are not allowed"),
            Self::EmptyComponent => f.write_str("empty path component"),
            Self::CurrentDirComponent => f.write_str("`.` components are not allowed"),
            Self::ParentDirComponent => f.write_str(
                "`..` components are not allowed; paths cannot leave the game directory",
            ),
            Self::Colon => {
                f.write_str("`:` is not allowed (drive letters, alternate data streams)")
            }
            Self::ReservedCharacter(c) => write!(f, "the character {c:?} is reserved on Windows"),
            Self::ControlCharacter(code) => write!(f, "control character U+{code:04X}"),
            Self::TrailingDotOrSpace => f.write_str("names must not end with a space or a period"),
            Self::ReservedName(name) => write!(f, "{name:?} is a reserved Windows device name"),
            Self::ComponentTooLong(len) => {
                write!(f, "a component is {len} bytes; the limit is 255")
            }
        }
    }
}
