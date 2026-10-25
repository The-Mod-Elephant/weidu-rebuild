use std::fs;
use std::process::{Command, Output};

use tempfile::TempDir;

fn iemod(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_iemod"))
        .args(args)
        .output()
        .unwrap()
}

#[test]
fn version_and_help() {
    let output = iemod(&["--version"]);
    assert!(output.status.success());
    let expected = option_env!("IEMOD_RELEASE_VERSION").unwrap_or("0.0.0-dev");
    assert_eq!(
        String::from_utf8(output.stdout).unwrap().trim(),
        format!("iemod {expected}")
    );
    assert!(
        String::from_utf8(iemod(&["--help"]).stdout)
            .unwrap()
            .contains("doctor")
    );
}

#[test]
fn doctor_succeeds_or_fails_with_a_message() {
    let dir = TempDir::new().unwrap();
    let path = dir.path().to_str().unwrap();
    let failed = iemod(&["doctor", "--game", path]);
    assert_eq!(failed.status.code(), Some(1));
    assert!(
        String::from_utf8(failed.stderr)
            .unwrap()
            .starts_with("error: ")
    );

    fs::write(dir.path().join("chitin.key"), b"KEY V1  ").unwrap();
    let ok = iemod(&["doctor", "--game", path]);
    assert_eq!(
        ok.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&ok.stderr)
    );

    let missing = dir.path().join("absent");
    assert_eq!(
        iemod(&["doctor", "--game", missing.to_str().unwrap()])
            .status
            .code(),
        Some(1)
    );
}
