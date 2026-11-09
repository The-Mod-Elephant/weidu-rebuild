mod cli;
mod version;
#[cfg_attr(
    not(test),
    expect(dead_code, reason = "no game-directory I/O uses the vfs module yet")
)]
mod vfs;

use std::process::ExitCode;

use clap::Parser;

use crate::cli::Cli;

fn main() -> ExitCode {
    Cli::parse();
    ExitCode::SUCCESS
}
