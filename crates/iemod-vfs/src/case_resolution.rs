//! Case-insensitive resolution of game paths against the real directory tree.
//!
//! The Infinity Engine was written for Windows, whose filesystems compare names
//! case-insensitively, and mods routinely refer to `OVERRIDE/Foo.ITM` when the file on disk is
//! `override/foo.itm`. On case-sensitive filesystems (Linux, some macOS volumes) those are
//! different names, so every lookup maps each requested component onto the single directory
//! entry that matches it ignoring case. Only ASCII letters are folded, a deliberate choice that
//! keeps the result independent of locale and Unicode version; non-ASCII characters must match
//! exactly.

use std::io;

use cap_std::fs::Dir;

use crate::error::VfsError;
use crate::rel_path::{RelPath, validate_component};

/// Result of resolving one path.
#[derive(Debug, PartialEq, Eq)]
pub enum Resolution {
    /// Every component exists; the path carries the on-disk spelling.
    Found(RelPath),
    /// The first `existing` components exist (spelled as on disk in `prefix`); the rest do not.
    Missing {
        /// On-disk spelling of the longest existing prefix (`None` when nothing matched).
        prefix: Option<RelPath>,
        /// How many leading components of the request exist.
        existing: usize,
    },
}

/// Map `request` onto the on-disk spelling of each component under `root`.
///
/// # Errors
///
/// [`VfsError::Ambiguous`] when a directory holds several names equal ignoring case, and
/// [`VfsError::Io`] when a directory cannot be listed (including `cap-std` refusing to follow
/// a symlink out of the root).
pub fn resolve(root: &Dir, request: &RelPath) -> Result<Resolution, VfsError> {
    let mut resolved: Vec<String> = Vec::with_capacity(request.components().len());
    for (index, wanted) in request.components().enumerate() {
        let listing = if resolved.is_empty() {
            root.entries()
        } else {
            root.read_dir(RelPath::with_components(resolved.clone()).to_native())
        };
        let entries = match listing {
            Ok(entries) => entries,
            // The previous component exists but is a regular file, so nothing can be below it.
            Err(error) if error.kind() == io::ErrorKind::NotADirectory => {
                return Ok(missing(resolved, index));
            }
            Err(source) => return Err(io_error("list the directory of", request, source)),
        };
        let mut matches = Vec::new();
        for entry in entries {
            let entry =
                entry.map_err(|source| io_error("list the directory of", request, source))?;
            // Names that are not valid UTF-8, or that RelPath would reject, can never be the
            // target of a mod path, so they are skipped rather than treated as matches.
            if let Ok(name) = entry.file_name().into_string()
                && validate_component(&name).is_ok()
                && name.eq_ignore_ascii_case(wanted)
            {
                matches.push(name);
            }
        }
        match matches.len() {
            0 => return Ok(missing(resolved, index)),
            1 => resolved.extend(matches),
            _ => {
                matches.sort();
                return Err(VfsError::Ambiguous {
                    path: request.to_string(),
                    candidates: matches,
                });
            }
        }
    }
    Ok(Resolution::Found(RelPath::with_components(resolved)))
}

fn missing(resolved: Vec<String>, existing: usize) -> Resolution {
    let prefix = (!resolved.is_empty()).then(|| RelPath::with_components(resolved));
    Resolution::Missing { prefix, existing }
}

fn io_error(operation: &'static str, path: &RelPath, source: io::Error) -> VfsError {
    VfsError::Io {
        operation,
        path: path.to_string(),
        source,
    }
}
