//! Behavioural tests of `GameRoot` against real temporary directories, including deliberate
//! escape attempts. Platform-specific cases (symlinks, hard links, case-sensitive filesystems)
//! check their preconditions at runtime and are skipped where they cannot be set up.

// Integration-test files are test-only crates; their helper functions sit outside `#[test]`, so
// clippy.toml's `allow-*-in-tests` settings do not reach them. Panicking is how tests fail.
#![allow(clippy::unwrap_used, clippy::panic)]

use std::fs;
use std::path::Path;

use iemod_vfs::{GameRoot, RelPath, VfsError};
use tempfile::TempDir;

fn rel(path: &str) -> RelPath {
    RelPath::parse(path).unwrap()
}

fn game() -> (TempDir, GameRoot) {
    let dir = TempDir::new().unwrap();
    fs::create_dir(dir.path().join("override")).unwrap();
    fs::write(dir.path().join("chitin.key"), b"KEY V1  rest").unwrap();
    fs::write(dir.path().join("override").join("SPWI101.SPL"), b"spell").unwrap();
    let root = GameRoot::open(dir.path()).unwrap();
    (dir, root)
}

/// True when the filesystem under `dir` treats names case-sensitively.
fn case_sensitive(dir: &Path) -> bool {
    fs::write(dir.join("probe"), b"").unwrap();
    let sensitive = !dir.join("PROBE").exists();
    fs::remove_file(dir.join("probe")).unwrap();
    sensitive
}

#[test]
fn reads_case_insensitively() {
    let (_dir, root) = game();
    assert_eq!(root.read(&rel("OVERRIDE\\spwi101.spl")).unwrap(), b"spell");
    assert_eq!(
        root.locate(&rel("Chitin.KEY")).unwrap().to_string(),
        "chitin.key"
    );
    assert_eq!(
        root.read_prefix(&rel("chitin.key"), 8).unwrap(),
        b"KEY V1  "
    );
    assert_eq!(
        root.read_prefix(&rel("chitin.key"), 1000).unwrap(),
        b"KEY V1  rest"
    );
}

#[test]
fn missing_paths_are_not_found() {
    let (_dir, root) = game();
    for missing in [
        "nope.itm",
        "override/nope.itm",
        "nope/x.itm",
        "chitin.key/below",
    ] {
        assert!(
            matches!(root.read(&rel(missing)), Err(VfsError::NotFound { .. })),
            "{missing}"
        );
    }
}

#[test]
fn open_reports_missing_root() {
    let dir = TempDir::new().unwrap();
    let error = GameRoot::open(&dir.path().join("absent")).unwrap_err();
    assert!(matches!(error, VfsError::OpenRoot { .. }));
}

#[test]
fn ambiguous_case_variants_are_rejected() {
    let (dir, root) = game();
    if !case_sensitive(dir.path()) {
        return; // cannot create two names differing only by case here
    }
    fs::write(dir.path().join("override").join("spwi101.spl"), b"other").unwrap();
    match root.read(&rel("override/SPWI101.SPL")) {
        Err(VfsError::Ambiguous { candidates, .. }) => {
            assert_eq!(candidates, ["SPWI101.SPL", "spwi101.spl"]);
        }
        other => panic!("expected ambiguity, got {other:?}"),
    }
}

#[test]
fn atomic_write_creates_replaces_and_keeps_spelling() {
    let (dir, root) = game();
    root.write_atomic(&rel("override/NEW/dir/file.itm"), b"one")
        .unwrap();
    assert_eq!(
        fs::read(dir.path().join("override/NEW/dir/file.itm")).unwrap(),
        b"one"
    );
    // Existing components keep their on-disk spelling whatever case the request uses.
    root.write_atomic(&rel("OVERRIDE/spwi101.spl"), b"replaced")
        .unwrap();
    assert_eq!(
        fs::read(dir.path().join("override").join("SPWI101.SPL")).unwrap(),
        b"replaced"
    );
    // No temporary files are left behind.
    let leftovers: Vec<_> = fs::read_dir(dir.path().join("override"))
        .unwrap()
        .map(|e| e.unwrap().file_name().into_string().unwrap())
        .filter(|name| name.contains(".iemod-tmp-"))
        .collect();
    assert!(leftovers.is_empty(), "{leftovers:?}");
}

#[test]
fn write_through_a_file_fails_without_side_effects() {
    let (dir, root) = game();
    let error = root
        .write_atomic(&rel("chitin.key/inner"), b"x")
        .unwrap_err();
    assert!(matches!(error, VfsError::Io { .. }), "{error:?}");
    assert_eq!(
        fs::read(dir.path().join("chitin.key")).unwrap(),
        b"KEY V1  rest"
    );
}

#[cfg(unix)]
#[test]
fn symlinks_cannot_escape_the_root() {
    use std::io::ErrorKind;
    use std::os::unix::fs::symlink;

    let outside = TempDir::new().unwrap();
    fs::write(outside.path().join("secret.txt"), b"secret").unwrap();
    let (dir, root) = game();
    symlink(outside.path(), dir.path().join("escape")).unwrap();
    symlink(
        outside.path().join("secret.txt"),
        dir.path().join("link.txt"),
    )
    .unwrap();
    // `override/up` climbs two levels, i.e. out of the game root.
    symlink("../../", dir.path().join("override").join("up")).unwrap();

    for attempt in ["escape/secret.txt", "link.txt", "override/up/chitin.key"] {
        let error = root.read(&rel(attempt)).unwrap_err();
        let VfsError::Io { source, .. } = &error else {
            panic!("{attempt}: expected an I/O refusal, got {error:?}");
        };
        assert_eq!(source.kind(), ErrorKind::PermissionDenied, "{attempt}");
    }
    let error = root
        .write_atomic(&rel("escape/planted.txt"), b"x")
        .unwrap_err();
    assert!(matches!(error, VfsError::Io { .. }), "{error:?}");
    assert!(!outside.path().join("planted.txt").exists());

    // Symlinks that stay inside the root keep working, including ones that use `..` internally.
    symlink("override", dir.path().join("alias")).unwrap();
    assert_eq!(root.read(&rel("alias/SPWI101.SPL")).unwrap(), b"spell");
    symlink("../", dir.path().join("override").join("back")).unwrap();
    assert_eq!(
        root.read(&rel("override/back/chitin.key")).unwrap(),
        b"KEY V1  rest"
    );
}

#[cfg(unix)]
#[test]
fn hard_links_are_replaced_not_written_through() {
    let outside = TempDir::new().unwrap();
    let victim = outside.path().join("victim.txt");
    fs::write(&victim, b"original").unwrap();
    let (dir, root) = game();
    if fs::hard_link(&victim, dir.path().join("linked.txt")).is_err() {
        return; // temporary directories on different filesystems
    }
    root.write_atomic(&rel("linked.txt"), b"mod data").unwrap();
    assert_eq!(fs::read(&victim).unwrap(), b"original");
    assert_eq!(
        fs::read(dir.path().join("linked.txt")).unwrap(),
        b"mod data"
    );
}
