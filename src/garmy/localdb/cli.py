"""Legacy CLI module - redirects to new modular CLI structure."""

# Import the new modular CLI
from .cli.commands import main as cli_main


# For backward compatibility, expose the main CLI function
def main():
    """Main CLI entry point."""
    cli_main()

# Alias for backward compatibility
cli = cli_main

if __name__ == '__main__':
    main()
