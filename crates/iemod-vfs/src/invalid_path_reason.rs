//! The individual rules a game-relative path can violate.

use std::fmt;

/// Why a path was rejected by [`RelPath::parse`](crate::RelPath::parse).
///
/// The rules combine two goals. First, *containment*: nothing may name a location outside the
/// game root (absolute paths, drive or UNC prefixes, `..`). Second, *portability*: a mod must
/// behave identically on Windows, macOS and Linux, so every name Windows cannot represent is
/// rejected everywhere. The Windows rules come from Microsoft's "Naming Files, Paths, and
/// Namespaces" (<https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file>).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InvalidPathReason {
    /// The path is empty.
    Empty,
    /// The path starts with a separator, so it would be resolved from a filesystem root.
    Absolute,
    /// Two separators in a row, or a trailing separator, produce an empty component.
    EmptyComponent,
    /// A `.` component. It is harmless but ambiguous in diagnostics, so it is rejected.
    CurrentDirComponent,
    /// A `..` component, the classic traversal vector.
    ParentDirComponent,
    /// A `:` anywhere: drive designators (`C:`) and NTFS alternate data streams (`file:stream`).
    Colon,
    /// One of the characters Windows reserves in names: `< > " | ? *`.
    ReservedCharacter(char),
    /// A NUL or other control character (code points 1 through 31 are invalid on Windows).
    ControlCharacter(u32),
    /// A name ending in a space or a period, which Windows silently strips, so two different
    /// mod paths could otherwise alias the same file.
    TrailingDotOrSpace,
    /// A Windows device name such as `CON` or `LPT1`, with or without an extension.
    ReservedName(String),
    /// A component longer than 255 bytes, the limit of common filesystems such as ext4 and
    /// (in UTF-16 units, which a 255-byte UTF-8 string never exceeds) NTFS.
    ComponentTooLong(usize),
}

impl fmt::Display for InvalidPathReason {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Empty => f.write_str("the path is empty"),
            Self::Absolute => f.write_str(
                "absolute paths are not allowed; use a path relative to the game directory",
            ),
            Self::EmptyComponent => {
                f.write_str("the path contains an empty component (`//` or a trailing separator)")
            }
            Self::CurrentDirComponent => f.write_str("`.` components are not allowed"),
            Self::ParentDirComponent => f.write_str(
                "`..` components are not allowed; paths cannot leave the game directory",
            ),
            Self::Colon => {
                f.write_str("`:` is not allowed (drive letters and alternate data streams)")
            }
            Self::ReservedCharacter(c) => write!(f, "the character {c:?} is reserved on Windows"),
            Self::ControlCharacter(code) => {
                write!(f, "control character U+{code:04X} is not allowed")
            }
            Self::TrailingDotOrSpace => f.write_str("names must not end with a space or a period"),
            Self::ReservedName(name) => write!(f, "{name:?} is a reserved Windows device name"),
            Self::ComponentTooLong(len) => {
                write!(f, "a component is {len} bytes long; the limit is 255")
            }
        }
    }
}
