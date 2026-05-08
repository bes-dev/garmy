"""MCP server for Garmin LocalDB database access.

Provides secure, read-only access to synchronized health data through
the Model Context Protocol, enabling AI assistants to query health metrics.
"""

try:
    from .config import MCPConfig
    from .server import create_mcp_server

    __all__ = ["MCPConfig", "create_mcp_server"]
except ImportError:
    # FastMCP not installed
    __all__ = []
