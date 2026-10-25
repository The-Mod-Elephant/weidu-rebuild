//! Command-line grammar of the `iemod` executable.

use std::path::PathBuf;

use clap::{Parser, Subcommand};

use crate::version::VERSION;

/// Install and inspect Infinity Engine mods safely.
#[derive(Debug, Parser)]
#[command(name = "iemod", version = VERSION, about, long_about = None)]
#[command(after_help = "Exit status: 0 success, 1 check failed, 2 usage error, 3 access failed.")]
pub struct Cli {
    /// The operation to perform.
    #[command(subcommand)]
    pub command: Command,
}

/// Top-level subcommands. Each one maps to a module under `commands/`.
#[derive(Debug, Subcommand)]
pub enum Command {
    /// Check that a directory is a usable Infinity Engine game installation.
    Doctor {
        /// The game installation directory (the one containing `chitin.key`).
        #[arg(long, value_name = "DIR")]
        game: PathBuf,
    },
}

#[cfg(test)]
mod tests {
    use clap::CommandFactory;

    use super::Cli;

    #[test]
    fn grammar_is_consistent() {
        // clap's own self-check catches conflicting or malformed argument definitions.
        Cli::command().debug_assert();
    }
}
