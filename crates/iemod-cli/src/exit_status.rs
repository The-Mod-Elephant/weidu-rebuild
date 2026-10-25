//! Process exit statuses, documented so scripts and installers can react precisely.

use std::process::ExitCode;

/// Exit statuses of the `iemod` executable.
///
/// `2` is reserved for command-line usage errors, which `clap` reports itself with that status.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExitStatus {
    /// The command completed and every check passed.
    Success,
    /// The command ran but found a problem with the inspected data (for example, the directory
    /// is not an Infinity Engine game).
    CheckFailed,
    /// The command could not access the data it needed (missing directory, permissions, I/O).
    AccessFailed,
}

impl ExitStatus {
    /// The numeric status.
    #[must_use]
    pub const fn code(self) -> u8 {
        match self {
            Self::Success => 0,
            Self::CheckFailed => 1,
            Self::AccessFailed => 3,
        }
    }
}

impl From<ExitStatus> for ExitCode {
    fn from(status: ExitStatus) -> Self {
        Self::from(status.code())
    }
}
