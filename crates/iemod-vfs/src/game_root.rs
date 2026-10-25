use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use cap_std::ambient_authority;
use cap_std::fs::{Dir, OpenOptions};

use crate::case_resolution::{Resolution, resolve};
use crate::error::VfsError;
use crate::rel_path::RelPath;

static TEMP_COUNTER: AtomicU64 = AtomicU64::new(0);

/// An opened game directory; every access is confined to it.
///
/// Per the `cap-std` README, `Dir` "automatically protects against paths which might include
/// `..`, symlinks, or absolute paths that might lead outside of that `Dir`".
///
/// There is deliberately no delete operation (`docs/architecture/THREAT_MODEL.md`, T4).
#[derive(Debug)]
pub struct GameRoot {
    dir: Dir,
    path: PathBuf,
}

impl GameRoot {
    /// The only use of ambient authority: the user chose this directory explicitly.
    ///
    /// # Errors
    ///
    /// [`VfsError::OpenRoot`].
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

    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// The on-disk spelling of `request`.
    ///
    /// # Errors
    ///
    /// [`VfsError::NotFound`], [`VfsError::Ambiguous`] or [`VfsError::Io`].
    pub fn locate(&self, request: &RelPath) -> Result<RelPath, VfsError> {
        match resolve(&self.dir, request)? {
            Resolution::Found(path) => Ok(path),
            Resolution::Missing { .. } => Err(VfsError::NotFound {
                path: request.to_string(),
            }),
        }
    }

    /// # Errors
    ///
    /// As [`GameRoot::locate`], or [`VfsError::Io`].
    pub fn read(&self, request: &RelPath) -> Result<Vec<u8>, VfsError> {
        let actual = self.locate(request)?;
        self.dir
            .read(actual.to_native())
            .map_err(|source| io_error("read", request, source))
    }

    /// For sniffing a header without loading a multi-megabyte file.
    ///
    /// # Errors
    ///
    /// As [`GameRoot::locate`], or [`VfsError::Io`].
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

    /// Readers see either the old or the new contents, never a partial write. Existing parts of
    /// the path keep their on-disk spelling.
    ///
    /// Writing a temporary file and renaming it over the destination replaces a planted hard
    /// link instead of writing through it to a file outside the game directory.
    ///
    /// # Errors
    ///
    /// As [`GameRoot::locate`], or [`VfsError::Io`]; the destination is then unchanged.
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
            // Only ever removes the temporary file this call created.
            let _ = self.dir.remove_file(temp.to_native());
            return Err(io_error("write", request, source));
        }
        Ok(())
    }

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

    /// `create_new` in `write_new` turns any name collision into an error, never an overwrite.
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
