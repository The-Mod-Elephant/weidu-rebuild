use std::path::Path;

use iemod_formats::{FormatError, Header, KEY_V1};
use iemod_vfs::{GameRoot, RelPath, VfsError};

/// Every Infinity Engine game ships its resource index in the installation root.
const KEY_FILE: &str = "chitin.key";

#[derive(Debug, thiserror::Error)]
pub enum DoctorError {
    #[error(transparent)]
    Vfs(#[from] VfsError),
    #[error("{path} is not a valid KEY V1 file: {source}")]
    Format { path: String, source: FormatError },
}

/// Returns the human-readable report on success.
///
/// # Errors
///
/// [`DoctorError`] when the directory cannot be read or is not a game installation.
pub fn run(game: &Path) -> Result<String, DoctorError> {
    let root = GameRoot::open(game)?;
    let actual = root.locate(&RelPath::parse(KEY_FILE)?)?;
    // chitin.key can be several megabytes; only the header is needed.
    let prefix = root.read_prefix(&actual, Header::LEN as u64)?;
    KEY_V1
        .expect_in(&prefix)
        .map_err(|source| DoctorError::Format {
            path: actual.to_string(),
            source,
        })?;
    Ok(format!(
        "ok: {} is an Infinity Engine game directory ({actual} has a {KEY_V1} header)",
        game.display()
    ))
}

#[cfg(test)]
mod tests {
    use std::fs;

    use tempfile::TempDir;

    use super::*;

    #[test]
    fn accepts_a_game_directory_case_insensitively() {
        let dir = TempDir::new().unwrap();
        fs::write(dir.path().join("CHITIN.KEY"), b"KEY V1  \x01\x00\x00\x00").unwrap();
        let report = run(dir.path()).unwrap();
        assert!(
            report.contains("CHITIN.KEY has a \"KEY \" \"V1  \" header"),
            "{report}"
        );
    }

    #[test]
    fn rejects_missing_or_wrong_key_file() {
        let dir = TempDir::new().unwrap();
        let error = run(dir.path()).unwrap_err().to_string();
        assert!(error.contains("chitin.key does not exist"), "{error}");

        fs::write(dir.path().join("chitin.key"), b"BIFFV1  ").unwrap();
        let error = run(dir.path()).unwrap_err().to_string();
        assert!(error.contains("not a valid KEY V1 file"), "{error}");

        fs::write(dir.path().join("chitin.key"), b"KEY").unwrap();
        let error = run(dir.path()).unwrap_err().to_string();
        assert!(error.contains("truncated"), "{error}");
    }

    #[test]
    fn reports_inaccessible_directories() {
        let dir = TempDir::new().unwrap();
        let error = run(&dir.path().join("missing")).unwrap_err().to_string();
        assert!(error.contains("cannot open game directory"), "{error}");
    }
}
