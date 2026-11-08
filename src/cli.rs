use clap::Parser;

use crate::version::VERSION;

/// Install and inspect Infinity Engine mods safely.
#[derive(Debug, Parser)]
#[command(name = "iemod", version = VERSION, arg_required_else_help = true)]
pub struct Cli {}
