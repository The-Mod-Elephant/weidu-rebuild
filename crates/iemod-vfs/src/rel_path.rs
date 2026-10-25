use std::fmt;
use std::path::PathBuf;

use crate::error::VfsError;
use crate::invalid_path_reason::InvalidPathReason;

/// Reserved in every directory and with any extension (`NUL.txt` is `NUL`); Windows treats the
/// ISO/IEC 8859-1 superscripts as digits in `COM#`/`LPT#`. Source: Microsoft, "Naming Files,
/// Paths, and Namespaces".
const RESERVED_NAMES: [&str; 28] = [
    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8",
    "COM9", "COM¹", "COM²", "COM³", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8",
    "LPT9", "LPT¹", "LPT²", "LPT³",
];

const RESERVED_CHARACTERS: [char; 6] = ['<', '>', '"', '|', '?', '*'];

const MAX_COMPONENT_BYTES: usize = 255;

/// A non-empty, game-relative path made only of plain names.
///
/// Validation is lexical, so a mod path is accepted or rejected identically on every platform.
/// Both `/` and `\` separate components on input, since mods are authored on all platforms.
/// This is the first of two containment layers; `cap-std` enforces the second in
/// [`GameRoot`](crate::GameRoot).
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct RelPath {
    components: Vec<String>,
}

impl RelPath {
    /// # Errors
    ///
    /// [`VfsError::InvalidPath`] naming the first rule the input violates.
    pub fn parse(input: &str) -> Result<Self, VfsError> {
        let invalid = |reason| VfsError::InvalidPath {
            path: input.to_owned(),
            reason,
        };
        if input.is_empty() {
            return Err(invalid(InvalidPathReason::Empty));
        }
        // Also rejects UNC (`\\server\share`) and device (`\\?\`, `\\.\`) prefixes.
        if input.starts_with(['/', '\\']) {
            return Err(invalid(InvalidPathReason::Absolute));
        }
        let components = input
            .split(['/', '\\'])
            .map(|component| validate_component(component).map(|()| component.to_owned()))
            .collect::<Result<Vec<_>, _>>()
            .map_err(invalid)?;
        Ok(Self { components })
    }

    pub fn components(&self) -> impl ExactSizeIterator<Item = &str> {
        self.components.iter().map(String::as_str)
    }

    #[must_use]
    pub fn file_name(&self) -> &str {
        self.components.last().map_or("", String::as_str)
    }

    /// `None` for a path directly inside the game root.
    #[must_use]
    pub fn parent(&self) -> Option<Self> {
        match self.components.split_last() {
            Some((_, rest)) if !rest.is_empty() => Some(Self {
                components: rest.to_vec(),
            }),
            _ => None,
        }
    }

    /// For components that are already validated (requested ones, or names from a listing that
    /// passed `validate_component`).
    pub(crate) fn with_components(components: Vec<String>) -> Self {
        debug_assert!(!components.is_empty(), "RelPath must not be empty");
        Self { components }
    }

    #[must_use]
    pub fn to_native(&self) -> PathBuf {
        self.components.iter().collect()
    }
}

impl fmt::Display for RelPath {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.components.join("/"))
    }
}

pub(crate) fn validate_component(component: &str) -> Result<(), InvalidPathReason> {
    match component {
        "" => return Err(InvalidPathReason::EmptyComponent),
        "." => return Err(InvalidPathReason::CurrentDirComponent),
        ".." => return Err(InvalidPathReason::ParentDirComponent),
        _ => {}
    }
    if component.len() > MAX_COMPONENT_BYTES {
        return Err(InvalidPathReason::ComponentTooLong(component.len()));
    }
    for c in component.chars() {
        if c == ':' {
            return Err(InvalidPathReason::Colon);
        }
        if RESERVED_CHARACTERS.contains(&c) {
            return Err(InvalidPathReason::ReservedCharacter(c));
        }
        if u32::from(c) < 0x20 {
            return Err(InvalidPathReason::ControlCharacter(u32::from(c)));
        }
    }
    if component.ends_with([' ', '.']) {
        return Err(InvalidPathReason::TrailingDotOrSpace);
    }
    // "NUL.tar.gz" and "NUL .txt" are both the NUL device.
    let stem = component
        .split('.')
        .next()
        .unwrap_or(component)
        .trim_end_matches(' ');
    if let Some(reserved) = RESERVED_NAMES
        .iter()
        .find(|name| name.eq_ignore_ascii_case(stem))
    {
        return Err(InvalidPathReason::ReservedName((*reserved).to_owned()));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn reason(input: &str) -> InvalidPathReason {
        match RelPath::parse(input) {
            Err(VfsError::InvalidPath { reason, .. }) => reason,
            other => panic!("{input:?} should be rejected, got {other:?}"),
        }
    }

    #[test]
    fn accepts_plain_relative_paths_with_either_separator() {
        let path = RelPath::parse("override\\SPWI101.spl").unwrap();
        assert_eq!(
            path.components().collect::<Vec<_>>(),
            ["override", "SPWI101.spl"]
        );
        assert_eq!(path.to_string(), "override/SPWI101.spl");
        assert_eq!(path.file_name(), "SPWI101.spl");
        assert_eq!(path.parent().unwrap().to_string(), "override");
        assert!(RelPath::parse("chitin.key").unwrap().parent().is_none());
        for ok in [
            ".hidden",
            "a.b.c",
            "dir/sub/file",
            "ünïcödé.tra",
            "CONSOLE.txt",
            "COM10",
            "LPT0",
        ] {
            assert!(RelPath::parse(ok).is_ok(), "{ok:?} should be accepted");
        }
    }

    #[test]
    fn rejects_containment_violations() {
        assert_eq!(reason(""), InvalidPathReason::Empty);
        for absolute in [
            "/etc/passwd",
            "\\Windows",
            "\\\\server\\share",
            "\\\\?\\C:\\x",
            "//x",
        ] {
            assert_eq!(
                reason(absolute),
                InvalidPathReason::Absolute,
                "{absolute:?}"
            );
        }
        for traversal in ["..", "../x", "a/../../x", "a\\..\\x", "a/.."] {
            assert_eq!(
                reason(traversal),
                InvalidPathReason::ParentDirComponent,
                "{traversal:?}"
            );
        }
        assert_eq!(reason("./x"), InvalidPathReason::CurrentDirComponent);
        assert_eq!(reason("C:\\x"), InvalidPathReason::Colon);
        assert_eq!(reason("C:x"), InvalidPathReason::Colon);
        assert_eq!(reason("file.txt:stream"), InvalidPathReason::Colon);
        assert_eq!(reason("a//b"), InvalidPathReason::EmptyComponent);
        assert_eq!(reason("a/"), InvalidPathReason::EmptyComponent);
    }

    #[test]
    fn rejects_names_windows_cannot_represent() {
        for c in RESERVED_CHARACTERS {
            assert_eq!(
                reason(&format!("a{c}b")),
                InvalidPathReason::ReservedCharacter(c)
            );
        }
        assert_eq!(reason("a\0b"), InvalidPathReason::ControlCharacter(0));
        assert_eq!(reason("a\x1fb"), InvalidPathReason::ControlCharacter(0x1f));
        assert_eq!(reason("a\nb"), InvalidPathReason::ControlCharacter(0x0a));
        assert_eq!(reason("name."), InvalidPathReason::TrailingDotOrSpace);
        assert_eq!(reason("dir /x"), InvalidPathReason::TrailingDotOrSpace);
        for device in [
            "CON",
            "con",
            "nul.txt",
            "NUL.tar.gz",
            "Com1",
            "lpt9.itm",
            "COM¹",
            "AUX .x",
        ] {
            assert!(
                matches!(reason(device), InvalidPathReason::ReservedName(_)),
                "{device:?}"
            );
        }
        assert_eq!(
            reason(&"a".repeat(256)),
            InvalidPathReason::ComponentTooLong(256)
        );
        assert!(RelPath::parse(&"a".repeat(255)).is_ok());
    }
}
