mod cli;
mod version;

use std::process::ExitCode;

use clap::Parser;

use crate::cli::Cli;

fn main() -> ExitCode {
    Cli::parse();
    ExitCode::SUCCESS
}
