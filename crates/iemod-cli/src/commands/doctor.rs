//! `iemod doctor`: verify that a directory is an Infinity Engine game installation.

use std::io::Write;
use std::path::Path;

use iemod_formats::{FormatError, Header, KEY_V1};
use iemod_vfs::{GameRoot, RelPath, VfsError};

use crate::exit_status::ExitStatus;

/// The resource index every Infinity Engine game ships in its installation root.
const KEY_FILE: &str = "chitin.key";

/// Run the checks, writing a human-readable report to `out` and problems to `err`.
///
/// Write errors on the report streams are ignored deliberately: a closed pipe (e.g. `| head`)
/// must not turn a successful check into a failure.
pub fn run(game: &Path, out: &mut impl Write, err: &mut impl Write) -> ExitStatus {
    let root = match GameRoot::open(game) {
        Ok(root) => root,
        Err(error) => {
            let _ = writeln!(err, "error: {error}");
            let _ = writeln!(
                err,
                "hint: pass the game installation directory with --game <DIR>"
            );
            return ExitStatus::AccessFailed;
        }
    };
    match check_key(&root) {
        Ok(actual) => {
            let _ = writeln!(
                out,
                "ok: {} is an Infinity Engine game directory",
                game.display()
            );
            let _ = writeln!(out, "ok: {actual} has a {KEY_V1} header");
            ExitStatus::Success
        }
        Err(problem) => {
            let _ = writeln!(err, "error: {problem}");
            problem.status()
        }
    }
}

/// Why the directory failed the check.
#[derive(Debug, thiserror::Error)]
enum Problem {
    #[error(transparent)]
    Vfs(#[from] VfsError),
    #[error("{path} is not a valid KEY V1 file: {source}")]
    Format { path: String, source: FormatError },
}

impl Problem {
    fn status(&self) -> ExitStatus {
        match self {
            // The directory was readable but its contents are wrong.
            Self::Vfs(VfsError::NotFound { .. } | VfsError::Ambiguous { .. })
            | Self::Format { .. } => ExitStatus::CheckFailed,
            Self::Vfs(_) => ExitStatus::AccessFailed,
        }
    }
}

/// Locate `chitin.key` case-insensitively and validate its header; returns its on-disk name.
fn check_key(root: &GameRoot) -> Result<RelPath, Problem> {
    let request = RelPath::parse(KEY_FILE)?;
    let actual = root.locate(&request)?;
    // Only the header is needed; chitin.key can be several megabytes.
    let prefix = root.read_prefix(&actual, Header::LEN as u64)?;
    KEY_V1
        .expect_in(&prefix)
        .map_err(|source| Problem::Format {
            path: actual.to_string(),
            source,
        })?;
    Ok(actual)
}

#[cfg(test)]
mod tests {
    use std::fs;

    use tempfile::TempDir;

    use super::*;

    fn doctor(dir: &Path) -> (ExitStatus, String, String) {
        let (mut out, mut err) = (Vec::new(), Vec::new());
        let status = run(dir, &mut out, &mut err);
        (
            status,
            String::from_utf8(out).unwrap(),
            String::from_utf8(err).unwrap(),
        )
    }

    #[test]
    fn accepts_a_game_directory_case_insensitively() {
        let dir = TempDir::new().unwrap();
        fs::write(dir.path().join("CHITIN.KEY"), b"KEY V1  \x01\x00\x00\x00").unwrap();
        let (status, out, err) = doctor(dir.path());
        assert_eq!(status, ExitStatus::Success, "{err}");
        assert!(
            out.contains("ok: CHITIN.KEY has a \"KEY \" \"V1  \" header"),
            "{out}"
        );
    }

    #[test]
    fn rejects_missing_or_wrong_key_file() {
        let dir = TempDir::new().unwrap();
        let (status, _, err) = doctor(dir.path());
        assert_eq!(status, ExitStatus::CheckFailed);
        assert!(err.contains("chitin.key does not exist"), "{err}");

        fs::write(dir.path().join("chitin.key"), b"BIFFV1  ").unwrap();
        let (status, _, err) = doctor(dir.path());
        assert_eq!(status, ExitStatus::CheckFailed);
        assert!(err.contains("not a valid KEY V1 file"), "{err}");

        fs::write(dir.path().join("chitin.key"), b"KEY").unwrap();
        let (status, _, err) = doctor(dir.path());
        assert_eq!(status, ExitStatus::CheckFailed);
        assert!(err.contains("truncated"), "{err}");
    }

    #[test]
    fn reports_inaccessible_directories() {
        let dir = TempDir::new().unwrap();
        let (status, _, err) = doctor(&dir.path().join("missing"));
        assert_eq!(status, ExitStatus::AccessFailed);
        assert!(err.contains("cannot open game directory"), "{err}");
    }
}
