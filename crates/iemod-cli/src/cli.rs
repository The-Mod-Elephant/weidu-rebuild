use std::path::PathBuf;

use clap::{Parser, Subcommand};

use crate::version::VERSION;

/// Install and inspect Infinity Engine mods safely.
#[derive(Debug, Parser)]
#[command(name = "iemod", version = VERSION, about, long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Command,
}

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
        Cli::command().debug_assert();
    }
}
