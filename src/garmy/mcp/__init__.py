"""
Garmy MCP (Model Context Protocol) server for Claude Code integration.

This module provides MCP server functionality for LocalDB integration with Claude Code.

To run the MCP server:
    python -m garmy.mcp

Or import and use programmatically:
    from garmy.mcp import create_server
    server = create_server("/path/to/localdb.db")
    server.run()
"""

from .server import GarmyMCPServer, create_server, main

__all__ = ['GarmyMCPServer', 'create_server', 'main']
__version__ = "1.0.0"