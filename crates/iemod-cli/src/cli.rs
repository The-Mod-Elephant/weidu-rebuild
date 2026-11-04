use clap::Parser;

use crate::version::VERSION;

/// Install and inspect Infinity Engine mods safely.
#[derive(Debug, Parser)]
#[command(name = "iemod", version = VERSION, arg_required_else_help = true)]
pub struct Cli {}

#[cfg(test)]
mod tests {
    use clap::error::ErrorKind;
    use clap::{CommandFactory, Parser};

    use super::Cli;
    use crate::version::VERSION;

    #[test]
    fn grammar_is_consistent() {
        Cli::command().debug_assert();
    }

    #[test]
    fn version_flags_print_the_version() {
        for flag in ["--version", "-V"] {
            let error = Cli::try_parse_from(["iemod", flag]).unwrap_err();
            assert_eq!(error.kind(), ErrorKind::DisplayVersion, "{flag}");
            assert_eq!(error.to_string(), format!("iemod {VERSION}\n"), "{flag}");
            assert_eq!(error.exit_code(), 0, "{flag}");
        }
    }

    #[test]
    fn help_flags_print_the_help() {
        for flag in ["--help", "-h"] {
            let error = Cli::try_parse_from(["iemod", flag]).unwrap_err();
            assert_eq!(error.kind(), ErrorKind::DisplayHelp, "{flag}");
            let help = error.to_string();
            assert!(
                help.starts_with("Install and inspect Infinity Engine mods safely"),
                "{help}"
            );
            assert!(help.contains("Usage: iemod"), "{help}");
            assert_eq!(error.exit_code(), 0, "{flag}");
        }
    }

    #[test]
    fn no_arguments_print_the_help_and_fail() {
        let error = Cli::try_parse_from(["iemod"]).unwrap_err();
        assert_eq!(
            error.kind(),
            ErrorKind::DisplayHelpOnMissingArgumentOrSubcommand
        );
        assert!(error.to_string().contains("Usage: iemod"), "{error}");
        assert_eq!(error.exit_code(), 2);
    }

    #[test]
    fn unknown_arguments_are_rejected() {
        for argument in ["--unknown", "-x", "positional"] {
            let error = Cli::try_parse_from(["iemod", argument]).unwrap_err();
            assert_eq!(error.kind(), ErrorKind::UnknownArgument, "{argument}");
            assert_eq!(error.exit_code(), 2, "{argument}");
        }
    }
}
