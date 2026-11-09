use std::fmt::{self, Write};

use crate::vfs::{InvalidPath, InvalidPathReason};

/// Reserved in every directory, also when an extension follows (`NUL.txt` is `NUL`). Windows
/// treats the ISO/IEC 8859-1 superscripts as digits in `COM#` and `LPT#`.
/// Source: Microsoft Learn, "Naming Files, Paths, and Namespaces", Naming Conventions.
const RESERVED_NAMES: [&str; 28] = [
    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8",
    "COM9", "COM¹", "COM²", "COM³", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8",
    "LPT9", "LPT¹", "LPT²", "LPT³",
];

/// Source: Microsoft Learn, "Naming Files, Paths, and Namespaces", Naming Conventions. The other
/// reserved characters, `:`, `/` and `\`, have their own rules.
const RESERVED_CHARACTERS: [char; 6] = ['<', '>', '"', '|', '?', '*'];

/// The stricter of Linux `NAME_MAX` (255 bytes, `include/uapi/linux/limits.h`) and the Windows
/// component limit, "commonly 255 characters" in UTF-16 units (Microsoft Learn, "Maximum Path
/// Length Limitation"): a UTF-8 name is never shorter in bytes than in UTF-16 units.
const MAX_COMPONENT_BYTES: usize = 255;

/// A non-empty, game-relative path made only of plain names.
///
/// Validation is lexical, so a mod path is accepted or rejected identically on every platform,
/// and names Windows cannot represent are rejected everywhere (threats T1 and T6). Both `/` and
/// `\` separate components, since mods are authored on all platforms. Names are kept as written:
/// file systems treat them as opaque, so there is no Unicode normalization, and case folding is
/// left to lookups.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct RelPath {
    components: Vec<String>,
}

impl RelPath {
    /// # Errors
    ///
    /// [`InvalidPath`] naming the first rule the input violates.
    pub fn parse(input: &str) -> Result<Self, InvalidPath> {
        let invalid = |reason| InvalidPath {
            path: input.to_owned(),
            reason,
        };
        if input.is_empty() {
            return Err(invalid(InvalidPathReason::Empty));
        }
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
}

impl fmt::Display for RelPath {
    /// Components may still contain DEL and C1 control characters, which Windows accepts in
    /// names; they are escaped so a displayed path cannot drive the terminal (threat T9).
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        for (index, component) in self.components.iter().enumerate() {
            if index > 0 {
                f.write_char('/')?;
            }
            for c in component.chars() {
                if c.is_control() {
                    write!(f, "{}", c.escape_unicode())?;
                } else {
                    f.write_char(c)?;
                }
            }
        }
        Ok(())
    }
}

fn validate_component(component: &str) -> Result<(), InvalidPathReason> {
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
        // Code points 0-31 (Microsoft Learn, "Naming Files, Paths, and Namespaces").
        if u32::from(c) < 0x20 {
            return Err(InvalidPathReason::ControlCharacter(u32::from(c)));
        }
    }
    // Microsoft Learn, "Naming Files, Paths, and Namespaces": "Do not end a file or directory
    // name with a space or a period."
    if component.ends_with([' ', '.']) {
        return Err(InvalidPathReason::TrailingDotOrSpace);
    }
    // Deliberately stricter than the documented "followed immediately by an extension": spaces
    // before the first dot are ignored too, so `NUL .txt` is rejected.
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
            Err(InvalidPath { path, reason }) => {
                assert_eq!(path, input);
                reason
            }
            Ok(path) => panic!("{input:?} should be rejected, got {path:?}"),
        }
    }

    fn accepts(input: &str) -> RelPath {
        RelPath::parse(input).unwrap_or_else(|error| panic!("{input:?} rejected: {error}"))
    }

    #[test]
    fn splits_on_either_separator() {
        let path = accepts("override\\sub/SPWI101.spl");
        assert_eq!(
            path.components().collect::<Vec<_>>(),
            ["override", "sub", "SPWI101.spl"]
        );
        assert_eq!(path.components().len(), 3);
        assert_eq!(path.to_string(), "override/sub/SPWI101.spl");
        assert_eq!(accepts("chitin.key").components().len(), 1);
    }

    #[test]
    fn accepts_plain_names() {
        for ok in [
            ".hidden",
            "a.b.c",
            " leading space",
            "ünïcödé.tra",
            "日本語/ファイル",
            "a\u{7f}b",
            "a\u{85}b",
            "CONSOLE.txt",
            "NULL",
            "xNUL",
            "AUXI.txt",
            "COM1x",
            "COM0",
            "LPT0",
            "COM10",
            "ＣＯＮ",
            "x.CON",
        ] {
            accepts(ok);
        }
    }

    #[test]
    fn rejects_empty_and_absolute_paths() {
        assert_eq!(reason(""), InvalidPathReason::Empty);
        for absolute in [
            "/",
            "\\",
            "/etc/passwd",
            "\\Windows",
            "//x",
            "\\\\server\\share",
            "\\\\?\\C:\\x",
            "\\\\.\\COM1",
        ] {
            assert_eq!(
                reason(absolute),
                InvalidPathReason::Absolute,
                "{absolute:?}"
            );
        }
    }

    #[test]
    fn rejects_drives_and_streams() {
        for colon in [
            "C:",
            "C:\\x",
            "C:x",
            "c:/x",
            "a/C:",
            "file.txt:stream",
            "a::$DATA",
        ] {
            assert_eq!(reason(colon), InvalidPathReason::Colon, "{colon:?}");
        }
    }

    #[test]
    fn rejects_empty_and_relative_components() {
        for empty in ["a//b", "a/", "a\\", "a\\/b"] {
            assert_eq!(
                reason(empty),
                InvalidPathReason::EmptyComponent,
                "{empty:?}"
            );
        }
        for current in [".", "./x", "x/.", "a\\.\\b"] {
            assert_eq!(
                reason(current),
                InvalidPathReason::CurrentDirComponent,
                "{current:?}"
            );
        }
        for parent in ["..", "../x", "a/..", "a/../b", "a/../../x", "a\\..\\x"] {
            assert_eq!(
                reason(parent),
                InvalidPathReason::ParentDirComponent,
                "{parent:?}"
            );
        }
    }

    #[test]
    fn rejects_reserved_and_control_characters() {
        for c in RESERVED_CHARACTERS {
            assert_eq!(
                reason(&format!("a{c}b")),
                InvalidPathReason::ReservedCharacter(c)
            );
        }
        for code in 0..0x20_u8 {
            assert_eq!(
                reason(&format!("a{}b", char::from(code))),
                InvalidPathReason::ControlCharacter(u32::from(code)),
                "U+{code:04X}"
            );
        }
    }

    #[test]
    fn rejects_trailing_dots_and_spaces() {
        for trailing in ["name.", "name ", "...", "dir./x", "dir /x", "nul.", "a. "] {
            assert_eq!(
                reason(trailing),
                InvalidPathReason::TrailingDotOrSpace,
                "{trailing:?}"
            );
        }
    }

    #[test]
    fn rejects_device_names_in_any_case_and_position() {
        for name in RESERVED_NAMES {
            let lower = name.to_ascii_lowercase();
            let mixed: String = name
                .chars()
                .enumerate()
                .map(|(i, c)| {
                    if i % 2 == 0 {
                        c
                    } else {
                        c.to_ascii_lowercase()
                    }
                })
                .collect();
            for input in [
                name.to_owned(),
                lower.clone(),
                mixed,
                format!("{lower}.txt"),
                format!("{name}.tar.gz"),
                format!("{name} .txt"),
                format!("{name}/x"),
                format!("dir\\{lower}.itm"),
            ] {
                assert_eq!(
                    reason(&input),
                    InvalidPathReason::ReservedName(name.to_owned()),
                    "{input:?}"
                );
            }
        }
    }

    #[test]
    fn limits_component_length_in_utf8_bytes() {
        accepts(&"a".repeat(MAX_COMPONENT_BYTES));
        accepts(&"é".repeat(127));
        accepts(&format!("{}/{}", "a".repeat(255), "b".repeat(255)));
        assert_eq!(
            reason(&"a".repeat(256)),
            InvalidPathReason::ComponentTooLong(256)
        );
        assert_eq!(
            reason(&"é".repeat(128)),
            InvalidPathReason::ComponentTooLong(256)
        );
        assert_eq!(
            reason(&format!("ok/{}", "a".repeat(300))),
            InvalidPathReason::ComponentTooLong(300)
        );
    }

    #[test]
    fn displays_control_characters_escaped() {
        assert_eq!(
            accepts("a\u{7f}/b\u{9b}31m").to_string(),
            "a\\u{7f}/b\\u{9b}31m"
        );
    }

    #[test]
    fn error_display_escapes_untrusted_input() {
        let message = RelPath::parse("a\u{1b}[31m/..").unwrap_err().to_string();
        assert!(!message.contains('\u{1b}'), "{message:?}");
        assert_eq!(
            message,
            "invalid path \"a\\u{1b}[31m/..\": the path has the control character U+001B"
        );
        let message = RelPath::parse("a\u{9b}b/..").unwrap_err().to_string();
        assert!(!message.contains('\u{9b}'), "{message:?}");
        assert_eq!(
            message,
            "invalid path \"a\\u{9b}b/..\": the path has a `..` component"
        );
    }
}
