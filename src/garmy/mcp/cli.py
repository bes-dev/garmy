#!/usr/bin/env python3
"""Command-line interface for Garmin LocalDB MCP Server."""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from .config import MCPConfig

try:
    from .server import create_mcp_server
except ImportError:
    def create_mcp_server(*args, **kwargs):
        raise ImportError(
            "FastMCP is required for MCP server functionality. "
            "Install with: pip install garmy[mcp] or pip install fastmcp"
        )


def validate_database_path(db_path: str) -> Path:
    """Validate database path exists and is accessible.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        Validated Path object
        
    Raises:
        FileNotFoundError: If database file doesn't exist
        PermissionError: If database file is not readable
    """
    path = Path(db_path).resolve()
    
    if not path.exists():
        raise FileNotFoundError(f"Database file not found: {path}")
    
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    
    if not os.access(path, os.R_OK):
        raise PermissionError(f"Database file is not readable: {path}")
    
    return path


def cmd_server(args):
    """Start MCP server with specified configuration."""
    # Determine database path
    db_path_str = args.database or os.environ.get('GARMY_DB_PATH')
    
    if not db_path_str:
        print("Error: Database path must be provided via --database argument or GARMY_DB_PATH environment variable", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Validate database path
        db_path = validate_database_path(db_path_str)
        
        # Validate configuration parameters
        if args.max_rows > args.max_rows_absolute:
            print(f"Error: --max-rows ({args.max_rows}) cannot exceed --max-rows-absolute ({args.max_rows_absolute})", file=sys.stderr)
            sys.exit(1)
        
        if args.max_rows <= 0:
            print("Error: --max-rows must be positive", file=sys.stderr)
            sys.exit(1)
        
        if args.max_rows_absolute > 10000:
            print("Error: --max-rows-absolute cannot exceed 10000 for security reasons", file=sys.stderr)
            sys.exit(1)
        
        # Create config with CLI parameters
        config = MCPConfig(
            db_path=db_path,
            max_rows=args.max_rows,
            max_rows_absolute=args.max_rows_absolute,
            enable_query_logging=args.enable_query_logging,
            strict_validation=not args.disable_strict_validation
        )
        
        if args.verbose:
            print(f"Starting Garmin LocalDB MCP Server...")
            print(f"Database: {db_path}")
            print(f"Configuration:")
            print(f"  - Read-only access: enabled")
            print(f"  - Max rows per query: {config.max_rows}")
            print(f"  - Max rows absolute limit: {config.max_rows_absolute}")
            print(f"  - Query logging: {config.enable_query_logging}")
            print(f"  - Strict validation: {config.strict_validation}")
            print(f"Available tools: explore_database_structure, get_table_details, execute_sql_query, get_health_summary")
        
        # Create and run server with explicit config
        mcp_server = create_mcp_server(config)
        mcp_server.run()
        
    except (FileNotFoundError, PermissionError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Failed to start MCP server: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_info(args):
    """Show information about the database and MCP server configuration."""
    # Determine database path
    db_path_str = args.database or os.environ.get('GARMY_DB_PATH')
    
    if not db_path_str:
        print("Error: Database path must be provided via --database argument or GARMY_DB_PATH environment variable", file=sys.stderr)
        sys.exit(1)
    
    try:
        db_path = validate_database_path(db_path_str)
        
        # Get database info
        file_size = db_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        print("Garmin LocalDB MCP Server Information")
        print("=" * 40)
        print(f"Database file: {db_path}")
        print(f"File size: {file_size_mb:.2f} MB")
        print(f"Read access: {'✅ Available' if os.access(db_path, os.R_OK) else '❌ Denied'}")
        
        # Try to get table info
        try:
            from .server import DatabaseManager
            config = MCPConfig.from_db_path(db_path)
            db_manager = DatabaseManager(config)
            
            # Get table information
            tables_query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            tables = db_manager.execute_safe_query(tables_query)
            
            print(f"\\nAvailable tables: {len(tables)}")
            for table in tables:
                table_name = table['name']
                count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                count_result = db_manager.execute_safe_query(count_query)
                row_count = count_result[0]['count'] if count_result else 0
                print(f"  - {table_name}: {row_count:,} records")
            
        except Exception as e:
            print(f"\\nWarning: Could not analyze database structure: {e}")
        
        print("\\nMCP Server Tools:")
        print("  - explore_database_structure() - Discover available data")
        print("  - get_table_details(name) - Get table schema and samples")
        print("  - execute_sql_query(sql, params) - Run SQL queries safely")
        print("  - get_health_summary(user_id, days) - Quick health overview")
        
        print("\\nTo start MCP server:")
        print(f"  garmy-mcp server --database {db_path}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_config(args):
    """Show example configurations for different use cases."""
    print("Garmin LocalDB MCP Server - Configuration Examples")
    print("=" * 50)
    
    print("\\n📋 Basic Usage:")
    print("  garmy-mcp server --database health.db")
    
    print("\\n🏭 Production Configuration (restrictive):")
    print("  garmy-mcp server --database health.db \\\\")
    print("    --max-rows 100 \\\\")
    print("    --max-rows-absolute 500")
    
    print("\\n🔧 Development Configuration (permissive with logging):")
    print("  garmy-mcp server --database health.db \\\\")
    print("    --max-rows 2000 \\\\")
    print("    --enable-query-logging \\\\")
    print("    --verbose")
    
    print("\\n🐛 Debug Configuration (relaxed validation):")
    print("  garmy-mcp server --database health.db \\\\")
    print("    --disable-strict-validation \\\\")
    print("    --enable-query-logging \\\\")
    print("    --verbose")
    
    print("\\n🤖 Claude Desktop Integration:")
    print('  {')
    print('    "mcpServers": {')
    print('      "garmy-localdb": {')
    print('        "command": "garmy-mcp",')
    print('        "args": ["server", "--database", "/path/to/health.db", "--max-rows", "500"]')
    print('      }')
    print('    }')
    print('  }')
    
    print("\\n🔐 Security Settings:")
    print("  --max-rows: Limit rows per query (default: 1000, max: 5000)")
    print("  --max-rows-absolute: Hard security limit (default: 5000, max: 10000)")
    print("  --enable-query-logging: Log all SQL queries for debugging")
    print("  --disable-strict-validation: Allow relaxed SQL validation (not recommended)")


def create_parser():
    """Create argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="garmy-mcp",
        description="Garmin LocalDB MCP Server - Secure read-only access to health data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  garmy-mcp server --database health.db
  garmy-mcp info --database health.db
  garmy-mcp config
  
Use 'garmy-mcp <command> --help' for command-specific help.
        """
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    subparsers.required = True
    
    # Server command
    server_parser = subparsers.add_parser(
        'server',
        help='Start MCP server',
        description='Start the MCP server with specified configuration'
    )
    
    server_parser.add_argument(
        '--database', '-d',
        type=str,
        help="Path to Garmin LocalDB SQLite database file"
    )
    
    server_parser.add_argument(
        '--max-rows',
        type=int,
        default=1000,
        help="Maximum number of rows per query (default: 1000, max: 5000)"
    )
    
    server_parser.add_argument(
        '--max-rows-absolute',
        type=int,
        default=5000,
        help="Absolute maximum rows limit for security (default: 5000, max: 10000)"
    )
    
    server_parser.add_argument(
        '--enable-query-logging',
        action='store_true',
        help="Enable SQL query logging for debugging"
    )
    
    server_parser.add_argument(
        '--disable-strict-validation',
        action='store_true',
        help="Disable strict SQL validation (not recommended)"
    )
    
    server_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Enable verbose logging and configuration display"
    )
    
    server_parser.set_defaults(func=cmd_server)
    
    # Info command
    info_parser = subparsers.add_parser(
        'info',
        help='Show database and server information',
        description='Display information about the database and available MCP tools'
    )
    
    info_parser.add_argument(
        '--database', '-d',
        type=str,
        help="Path to Garmin LocalDB SQLite database file"
    )
    
    info_parser.set_defaults(func=cmd_info)
    
    # Config command
    config_parser = subparsers.add_parser(
        'config',
        help='Show configuration examples',
        description='Display example configurations for different use cases'
    )
    config_parser.set_defaults(func=cmd_config)
    
    return parser


def main():
    """Main entry point for garmy-mcp CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Execute the selected command
    args.func(args)


if __name__ == "__main__":
    main()