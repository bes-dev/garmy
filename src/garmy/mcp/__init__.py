"""Garmy MCP (Model Context Protocol) module.

This module provides MCP server functionality for Garmy, enabling AI assistants
to access Garmin Connect health and fitness data through the standardized MCP protocol.

Example:
    >>> from garmy.mcp import create_server
    >>> server = create_server()
    >>> server.run()

Classes:
    GarmyMCPServer: Main MCP server implementation.
    MCPConfig: Configuration for MCP server.

Functions:
    create_server: Factory function to create a configured MCP server.
    run_server: Convenience function to run a server with default settings.
"""

from typing import Optional

from .config import MCPConfig
from .server import GarmyMCPServer


def create_server(config: Optional[MCPConfig] = None) -> GarmyMCPServer:
    """Create a configured Garmy MCP server.

    Args:
        config: Optional configuration. Uses defaults if not provided.

    Returns:
        Configured GarmyMCPServer instance.

    Example:
        >>> from garmy.mcp import create_server
        >>> server = create_server()
        >>> server.run()
    """
    if config is None:
        config = MCPConfig()

    return GarmyMCPServer(config)


def run_server(
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
    path: str = "/mcp",
    config: Optional[MCPConfig] = None,
) -> None:
    """Create and run a Garmy MCP server with the specified transport.

    Args:
        transport: Transport type ("stdio" or "http").
        host: Host for HTTP transport.
        port: Port for HTTP transport.
        path: Path for HTTP transport.
        config: Optional server configuration.

    Example:
        >>> from garmy.mcp import run_server
        >>> run_server("stdio")  # For Claude Desktop
        >>> run_server("http", port=8080)  # For HTTP clients
    """
    server = create_server(config)

    if transport == "http":
        server.run(transport="streamable-http", host=host, port=port, path=path)
    elif transport == "stdio":
        server.run(transport="stdio")
    else:
        raise ValueError(f"Unknown transport: {transport}. Use 'stdio' or 'http'")


__all__ = ["GarmyMCPServer", "MCPConfig", "create_server", "run_server"]
