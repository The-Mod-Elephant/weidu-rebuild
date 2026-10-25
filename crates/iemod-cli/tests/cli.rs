//! End-to-end tests that run the compiled `iemod` binary, as users and installers do.

// Integration-test files are test-only crates; their helper functions sit outside `#[test]`, so
// clippy.toml's `allow-*-in-tests` settings do not reach them. Panicking is how tests fail.
#![allow(clippy::unwrap_used, clippy::panic)]

use std::fs;
use std::process::{Command, Output};

use tempfile::TempDir;

fn iemod(args: &[&str]) -> Output {
    // Cargo builds the binary for integration tests and exposes its path in this variable.
    Command::new(env!("CARGO_BIN_EXE_iemod"))
        .args(args)
        .output()
        .unwrap()
}

#[test]
fn version_and_help() {
    let output = iemod(&["--version"]);
    assert!(output.status.success());
    let text = String::from_utf8(output.stdout).unwrap();
    // Local and CI test builds never set IEMOD_RELEASE_VERSION.
    let expected = option_env!("IEMOD_RELEASE_VERSION").unwrap_or("0.0.0-dev");
    assert_eq!(text.trim(), format!("iemod {expected}"));

    let help = String::from_utf8(iemod(&["--help"]).stdout).unwrap();
    assert!(help.contains("doctor"), "{help}");
    assert!(help.contains("Exit status"), "{help}");
}

#[test]
fn usage_errors_exit_with_2() {
    assert_eq!(iemod(&[]).status.code(), Some(2));
    assert_eq!(iemod(&["doctor"]).status.code(), Some(2));
    assert_eq!(iemod(&["frobnicate"]).status.code(), Some(2));
}

#[test]
fn doctor_exit_statuses() {
    let dir = TempDir::new().unwrap();
    let path = dir.path().to_str().unwrap();
    assert_eq!(iemod(&["doctor", "--game", path]).status.code(), Some(1));
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
        Some(3)
    );
}
