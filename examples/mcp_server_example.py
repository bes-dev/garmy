#!/usr/bin/env python3
"""Example usage of the Garmin LocalDB MCP Server.

This example demonstrates how to programmatically create and configure
the MCP server with custom settings.
"""

import os
from pathlib import Path

try:
    from garmy.mcp import MCPConfig, create_mcp_server
except ImportError:
    print("FastMCP not installed. Install with: pip install garmy[mcp]")
    exit(1)


def main():
    """Demonstrate MCP server configuration and creation."""

    # Example 1: Create config from database path
    db_path = Path("health.db")

    # Check if database exists (for demo purposes)
    if not db_path.exists():
        print(
            f"Database {db_path} not found. Please run garmy-sync first to create health data."
        )
        print("Example: garmy-sync sync --last-days 7")
        return

    # Create custom configuration
    config = MCPConfig.from_db_path(
        db_path=db_path,
        max_rows=500,  # Limit to 500 rows per query
        enable_query_logging=True,  # Enable query logging for debugging
        strict_validation=True,  # Enable strict SQL validation
    )

    print("MCP Server Configuration:")
    print(f"  Database: {config.db_path}")
    print(f"  Max rows per query: {config.max_rows}")
    print(f"  Query logging: {config.enable_query_logging}")
    print(f"  Strict validation: {config.strict_validation}")

    # Validate configuration
    try:
        config.validate()
        print("✅ Configuration is valid")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return

    # Create MCP server with custom config
    print("\\nCreating MCP server...")
    mcp_server = create_mcp_server(config)

    print(f"✅ MCP server created: {mcp_server.name}")
    print("\\nAvailable tools:")
    print("  📊 explore_database_structure() - Start here to see available data")
    print("  🔍 get_table_details(table_name) - Get table structure and samples")
    print("  📈 execute_sql_query(query, params) - Run custom SQL queries on any table")
    print("  📋 get_health_summary(user_id, days) - Quick health overview")
    print("\\nAvailable resources:")
    print("  📚 health_data_guide() - Complete usage guide")

    print("\\n🚀 To start the server, run:")
    print(f"   garmy-mcp server --database {db_path}")
    print("\\n📋 With custom configuration:")
    print(
        f"   garmy-mcp server --database {db_path} --max-rows 500 --enable-query-logging"
    )
    print("\\n🔧 Or use environment variable:")
    print(f"   export GARMY_DB_PATH={db_path}")
    print("   garmy-mcp server --max-rows 200 --verbose")
    print("\\n📊 Get database information:")
    print(f"   garmy-mcp info --database {db_path}")
    print("\\n📋 Show configuration examples:")
    print("   garmy-mcp config")

    # Example 2: Environment-based configuration (backwards compatibility)
    print("\\n" + "=" * 50)
    print("Environment-based configuration example:")

    os.environ["GARMY_DB_PATH"] = str(db_path)
    env_server = create_mcp_server()  # Uses environment variable
    print(f"✅ Environment-based server created: {env_server.name}")


if __name__ == "__main__":
    main()
