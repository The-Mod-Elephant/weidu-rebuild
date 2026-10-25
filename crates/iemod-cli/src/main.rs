//! Entry point of the `iemod` executable.
//!
//! `main` only parses arguments and dispatches; every subcommand lives in `commands/` and
//! returns an [`ExitStatus`], so the documented exit codes are produced in exactly one place.

mod cli;
mod commands;
mod exit_status;
mod version;

use std::io;
use std::process::ExitCode;

use clap::Parser;

use crate::cli::{Cli, Command};
use crate::exit_status::ExitStatus;

fn main() -> ExitCode {
    // `Cli::parse` prints help/version or a usage error itself and exits (status 2 on errors).
    let cli = Cli::parse();
    let status: ExitStatus = match cli.command {
        Command::Doctor { game } => {
            commands::doctor::run(&game, &mut io::stdout().lock(), &mut io::stderr().lock())
        }
    };
    status.into()
}
