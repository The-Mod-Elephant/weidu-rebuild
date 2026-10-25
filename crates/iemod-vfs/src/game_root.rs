//! The capability handle through which every game-directory access is made.

use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use cap_std::ambient_authority;
use cap_std::fs::{Dir, OpenOptions};

use crate::case_resolution::{Resolution, resolve};
use crate::error::VfsError;
use crate::rel_path::RelPath;

/// Distinguishes temporary files created concurrently by this process.
static TEMP_COUNTER: AtomicU64 = AtomicU64::new(0);

/// An opened game directory. All reads and writes are confined to it.
///
/// Confinement has two layers. [`RelPath`] rejects absolute paths, `..`, drive and stream
/// syntax lexically. Then every access goes through a [`cap_std::fs::Dir`], which, per the
/// `cap-std` documentation, "automatically protects against paths which might include `..`,
/// symlinks, or absolute paths that might lead outside of that `Dir`", failing with
/// `PermissionDenied`. Symlinks that stay inside the root keep working.
///
/// The type intentionally offers **no delete or rename-away operation**: a mod can create or
/// replace files, but cannot remove anything (see `docs/architecture/THREAT_MODEL.md`).
#[derive(Debug)]
pub struct GameRoot {
    dir: Dir,
    path: PathBuf,
}

impl GameRoot {
    /// Open `path` as the game root.
    ///
    /// This is the only place where ambient filesystem authority is used: the user chose this
    /// directory explicitly on the command line.
    ///
    /// # Errors
    ///
    /// [`VfsError::OpenRoot`] when the directory does not exist or cannot be opened.
    pub fn open(path: &Path) -> Result<Self, VfsError> {
        let dir = Dir::open_ambient_dir(path, ambient_authority()).map_err(|source| {
            VfsError::OpenRoot {
                path: path.to_owned(),
                source,
            }
        })?;
        Ok(Self {
            dir,
            path: path.to_owned(),
        })
    }

    /// The directory this root was opened from, for display purposes only.
    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// The on-disk spelling of `request`, found case-insensitively.
    ///
    /// # Errors
    ///
    /// [`VfsError::NotFound`] if any component is missing, plus the errors of the resolver.
    pub fn locate(&self, request: &RelPath) -> Result<RelPath, VfsError> {
        match resolve(&self.dir, request)? {
            Resolution::Found(path) => Ok(path),
            Resolution::Missing { .. } => Err(VfsError::NotFound {
                path: request.to_string(),
            }),
        }
    }

    /// Read a whole file.
    ///
    /// # Errors
    ///
    /// Lookup errors from [`GameRoot::locate`] and [`VfsError::Io`].
    pub fn read(&self, request: &RelPath) -> Result<Vec<u8>, VfsError> {
        let actual = self.locate(request)?;
        self.dir
            .read(actual.to_native())
            .map_err(|source| io_error("read", request, source))
    }

    /// Read at most `limit` bytes from the start of a file, e.g. to sniff a format header
    /// without loading a multi-megabyte archive.
    ///
    /// # Errors
    ///
    /// Lookup errors from [`GameRoot::locate`] and [`VfsError::Io`].
    pub fn read_prefix(&self, request: &RelPath, limit: u64) -> Result<Vec<u8>, VfsError> {
        let actual = self.locate(request)?;
        let file = self
            .dir
            .open(actual.to_native())
            .map_err(|source| io_error("open", request, source))?;
        let mut buffer = Vec::new();
        file.take(limit)
            .read_to_end(&mut buffer)
            .map_err(|source| io_error("read", request, source))?;
        Ok(buffer)
    }

    /// Create or replace a file so that readers observe either the old or the new contents,
    /// never a partial write.
    ///
    /// Existing directories and an existing file are matched case-insensitively and keep their
    /// on-disk spelling; missing parts are created with the requested spelling. The data is
    /// written to a uniquely named temporary file in the destination directory, flushed to
    /// stable storage, then renamed over the destination. Renaming replaces a destination that
    /// is a hard link instead of writing through it, so a hard link planted in the game
    /// directory cannot redirect the write to a file elsewhere.
    ///
    /// # Errors
    ///
    /// Lookup errors and [`VfsError::Io`]. On failure the temporary file is removed and the
    /// destination is unchanged.
    pub fn write_atomic(&self, request: &RelPath, contents: &[u8]) -> Result<(), VfsError> {
        let target = self.target_for_write(request)?;
        if let Some(parent) = target.parent() {
            self.dir
                .create_dir_all(parent.to_native())
                .map_err(|source| io_error("create the directory for", request, source))?;
        }
        let temp = Self::temp_sibling(&target);
        let result = self.write_new(&temp, contents).and_then(|()| {
            self.dir
                .rename(temp.to_native(), &self.dir, target.to_native())
        });
        if let Err(source) = result {
            // Clean-up of a file this call itself created moments ago; it never touches
            // pre-existing data. A failure here is secondary to the original error.
            let _ = self.dir.remove_file(temp.to_native());
            return Err(io_error("write", request, source));
        }
        Ok(())
    }

    /// The path a write to `request` should land on, reusing existing on-disk spellings.
    fn target_for_write(&self, request: &RelPath) -> Result<RelPath, VfsError> {
        match resolve(&self.dir, request)? {
            Resolution::Found(path) => Ok(path),
            Resolution::Missing { prefix, existing } => {
                let mut components: Vec<String> = prefix
                    .map(|p| p.components().map(str::to_owned).collect())
                    .unwrap_or_default();
                components.extend(request.components().skip(existing).map(str::to_owned));
                Ok(RelPath::with_components(components))
            }
        }
    }

    /// A temporary name next to `target`. The `.iemod-tmp-` infix plus process id and counter
    /// make collisions with real files and with concurrent writers practically impossible, and
    /// `create_new` below turns any remaining collision into an error instead of an overwrite.
    fn temp_sibling(target: &RelPath) -> RelPath {
        let unique = TEMP_COUNTER.fetch_add(1, Ordering::Relaxed);
        let name = format!(
            ".{}.iemod-tmp-{}-{unique}",
            target.file_name(),
            std::process::id()
        );
        let mut components: Vec<String> = target
            .parent()
            .map(|p| p.components().map(str::to_owned).collect())
            .unwrap_or_default();
        components.push(name);
        RelPath::with_components(components)
    }

    fn write_new(&self, path: &RelPath, contents: &[u8]) -> io::Result<()> {
        let mut options = OpenOptions::new();
        options.write(true).create_new(true);
        let mut file = self.dir.open_with(path.to_native(), &options)?;
        file.write_all(contents)?;
        file.sync_all()
    }
}

fn io_error(operation: &'static str, path: &RelPath, source: io::Error) -> VfsError {
    VfsError::Io {
        operation,
        path: path.to_string(),
        source,
    }
}
