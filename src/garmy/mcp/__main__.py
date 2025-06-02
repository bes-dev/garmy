"""Entry point for running Garmy MCP CLI as a module.

This allows the MCP CLI to be executed using:
    python -m garmy.mcp.cli <command>
"""

from .cli import main

if __name__ == "__main__":
    main()
