"""Garmin LocalDB MCP Server implementation.

Provides secure, read-only access to synchronized Garmin health data
through the Model Context Protocol with optimized tools for LLM understanding.
"""

import os
import re
import sqlite3
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from fastmcp import FastMCP
except ImportError:
    raise ImportError(
        "FastMCP is required for MCP server functionality. "
        "Install with: pip install garmy[mcp] or pip install fastmcp"
    )

from .config import MCPConfig
from ..localdb.models import MetricType


class SQLiteConnection:
    """Secure SQLite connection context manager for read-only access."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
    
    def __enter__(self):
        """Open read-only SQLite connection."""
        self.conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close connection safely."""
        if self.conn:
            self.conn.close()


class QueryValidator:
    """SQL query validation and sanitization for read-only access."""
    
    ALLOWED_STATEMENTS = ('select', 'with')
    FORBIDDEN_KEYWORDS = {
        'insert', 'update', 'delete', 'drop', 'create', 'alter',
        'pragma', 'attach', 'detach', 'vacuum', 'analyze'
    }
    
    @classmethod
    def validate_query(cls, query: str) -> None:
        """Validate SQL query for read-only access.
        
        Args:
            query: SQL query to validate
            
        Raises:
            ValueError: If query is not safe for read-only access
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        query_lower = query.lower().strip()
        
        # Check if query starts with allowed statement
        if not any(query_lower.startswith(prefix) for prefix in cls.ALLOWED_STATEMENTS):
            allowed = ', '.join(cls.ALLOWED_STATEMENTS).upper()
            raise ValueError(f"Only {allowed} queries are allowed for security")
        
        # Check for forbidden keywords
        query_words = set(re.findall(r'\\b\\w+\\b', query_lower))
        forbidden_found = query_words.intersection(cls.FORBIDDEN_KEYWORDS)
        if forbidden_found:
            raise ValueError(f"Forbidden keywords found: {', '.join(forbidden_found)}")
        
        # Check for multiple statements
        if cls._contains_multiple_statements(query):
            raise ValueError("Multiple statements not allowed")
    
    @staticmethod
    def _contains_multiple_statements(sql: str) -> bool:
        """Check if SQL contains multiple statements."""
        in_single_quote = False
        in_double_quote = False
        
        for char in sql:
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif char == ';' and not in_single_quote and not in_double_quote:
                return True
        
        return False
    
    @staticmethod
    def add_row_limit(query: str, limit: int = 1000) -> str:
        """Add LIMIT clause if not present."""
        query_lower = query.lower()
        if 'limit' not in query_lower:
            return f"{query.rstrip(';')} LIMIT {limit}"
        return query


class DatabaseManager:
    """Manages database connections and basic operations."""
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self.validator = QueryValidator()
        self.logger = logging.getLogger("garmy.mcp.database")
        
        # Configure logging if enabled
        if config.enable_query_logging and not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def get_connection(self):
        """Get read-only database connection."""
        return SQLiteConnection(self.config.db_path)
    
    def execute_safe_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute validated query with safety checks."""
        # Validate query
        if self.config.strict_validation:
            self.validator.validate_query(query)
        
        # Add row limit
        original_query = query
        query = self.validator.add_row_limit(query, self.config.max_rows)
        
        # Log query if enabled
        if self.config.enable_query_logging:
            self.logger.info(f"Executing query: {query}")
            if params:
                self.logger.info(f"Parameters: {params}")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or [])
                results = [dict(row) for row in cursor.fetchall()]
                
                if self.config.enable_query_logging:
                    self.logger.info(f"Query returned {len(results)} rows")
                
                return results
        except sqlite3.Error as e:
            if self.config.enable_query_logging:
                self.logger.error(f"Query failed: {str(e)}")
            raise ValueError(f"Database error: {str(e)}")


# Initialize MCP server
def create_mcp_server(config: Optional[MCPConfig] = None) -> FastMCP:
    """Create and configure the Garmin LocalDB MCP server.
    
    Args:
        config: Optional MCP configuration. If None, loads from environment.
    """
    if config is None:
        # Fallback to environment variable for backwards compatibility
        if 'GARMY_DB_PATH' not in os.environ:
            raise ValueError("GARMY_DB_PATH environment variable must be set")
        
        db_path = Path(os.environ['GARMY_DB_PATH'])
        config = MCPConfig.from_db_path(db_path)
    
    # Validate configuration
    config.validate()
    
    # Initialize components
    db_manager = DatabaseManager(config)
    
    # Initialize MCP server with clear, LLM-friendly name
    mcp = FastMCP("Garmin Health Data Explorer")
    
    @mcp.tool()
    def explore_database_structure() -> Dict[str, Any]:
        """WHEN TO USE: When you need to understand what health data is available.
        
        This is your starting point for exploring Garmin health data. Use this tool first
        to see what tables and data types are available before running specific queries.
        
        Returns:
            Complete database structure with table descriptions and available data types
        """
        try:
            # Get all tables
            tables_query = """
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name
            """
            tables = db_manager.execute_safe_query(tables_query)
            table_names = [row['name'] for row in tables]
            
            # Get row counts for each table
            table_info = {}
            for table_name in table_names:
                count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                count_result = db_manager.execute_safe_query(count_query)
                
                table_info[table_name] = {
                    "row_count": count_result[0]['count'],
                    "description": _get_table_description(table_name)
                }
            
            return {
                "available_tables": table_info,
                "metric_types": [mt.value for mt in MetricType],
                "usage_tip": "Use 'execute_sql_query' to get specific data from any table, or 'get_table_details' to see column structure"
            }
        except Exception as e:
            raise ValueError(f"Failed to explore database: {str(e)}")
    
    @mcp.tool()
    def get_table_details(table_name: str) -> Dict[str, Any]:
        """WHEN TO USE: When you need to see the structure and sample data of a specific table.
        
        Use this after 'explore_database_structure' when you want to understand what columns
        are available in a table and see examples of the actual data.
        
        Args:
            table_name: Name of the health data table (e.g., 'daily_health_metrics', 'activities')
            
        Returns:
            Table structure with columns, data types, and sample records
        """
        if not table_name or not table_name.strip():
            raise ValueError("Table name cannot be empty")
        
        # Sanitize table name
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
            raise ValueError("Invalid table name format")
        
        try:
            # Verify table exists
            check_query = """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """
            check_result = db_manager.execute_safe_query(check_query, [table_name])
            
            if not check_result:
                available_tables = db_manager.execute_safe_query(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
                table_list = [row['name'] for row in available_tables]
                raise ValueError(f"Table '{table_name}' does not exist. Available tables: {', '.join(table_list)}")
            
            # Get table schema using PRAGMA
            schema_query = f"PRAGMA table_info({table_name})"
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(schema_query)
                columns = cursor.fetchall()
            
            column_info = [{
                'name': col[1],
                'type': col[2],
                'required': bool(col[3]),
                'is_primary_key': bool(col[5])
            } for col in columns]
            
            # Get sample data (latest 3 records)
            sample_query = f"SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT 3"
            sample_data = db_manager.execute_safe_query(sample_query)
            
            return {
                "table_name": table_name,
                "columns": column_info,
                "sample_data": sample_data,
                "description": _get_table_description(table_name),
                "usage_tip": f"Use 'execute_sql_query' with SELECT statements to get specific data from {table_name}"
            }
                
        except Exception as e:
            raise ValueError(f"Failed to get table details: {str(e)}")
    
    @mcp.tool()
    def execute_sql_query(
        query: str,
        params: Optional[List[Any]] = None
    ) -> List[Dict[str, Any]]:
        """WHEN TO USE: When you need to get specific data using SQL queries.
        
        This is the main tool for querying any data from the database. Use it to run SELECT queries
        to analyze health metrics, activities, sync status, or find patterns across any tables.
        
        IMPORTANT: Only SELECT and WITH queries are allowed for security.
        
        Args:
            query: SQL SELECT query (e.g., "SELECT metric_date, total_steps FROM daily_health_metrics WHERE user_id = 1")
            params: Optional list of parameters for ? placeholders in query
            
        Example queries:
        - Health metrics: "SELECT metric_date, sleep_duration_hours FROM daily_health_metrics WHERE user_id = 1 ORDER BY metric_date DESC LIMIT 10"
        - Activities: "SELECT activity_date, activity_name, duration_seconds FROM activities WHERE user_id = 1"
        - High step days: "SELECT metric_date, total_steps FROM daily_health_metrics WHERE total_steps > 10000"
        - Timeseries data: "SELECT timestamp, value FROM timeseries WHERE metric_type = 'heart_rate'"
        
        Returns:
            List of matching records as dictionaries
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        try:
            return db_manager.execute_safe_query(query, params)
        except Exception as e:
            raise ValueError(f"Query execution failed: {str(e)}")
    
    @mcp.tool()
    def get_health_summary(
        user_id: int = 1,
        days: int = 30
    ) -> Dict[str, Any]:
        """WHEN TO USE: When you want a quick overview of health metrics without writing SQL.
        
        This tool provides a ready-made summary of key health metrics over a specified period.
        Use this for getting an overview before diving into specific analysis.
        
        Args:
            user_id: User ID to analyze (default: 1)
            days: Number of recent days to analyze (max 365, default: 30)
            
        Returns:
            Summary statistics including averages for steps, sleep, heart rate, stress, and activity count
        """
        if days > 365:
            raise ValueError("Days cannot exceed 365")
        
        if user_id < 1:
            raise ValueError("User ID must be positive")
        
        try:
            # Get health metrics summary
            summary_query = """
                SELECT 
                    COUNT(*) as total_days_with_data,
                    ROUND(AVG(total_steps), 0) as avg_daily_steps,
                    ROUND(AVG(sleep_duration_hours), 1) as avg_sleep_hours,
                    ROUND(AVG(resting_heart_rate), 0) as avg_resting_hr,
                    ROUND(AVG(avg_stress_level), 0) as avg_stress_level,
                    MIN(metric_date) as earliest_data_date,
                    MAX(metric_date) as latest_data_date
                FROM daily_health_metrics 
                WHERE user_id = ? 
                AND metric_date >= date('now', '-' || ? || ' days')
            """
            
            summary_result = db_manager.execute_safe_query(summary_query, [user_id, days])
            summary = summary_result[0] if summary_result else {}
            
            # Get activity count
            activity_query = """
                SELECT COUNT(*) as activity_count
                FROM activities 
                WHERE user_id = ? 
                AND activity_date >= date('now', '-' || ? || ' days')
            """
            
            activity_result = db_manager.execute_safe_query(activity_query, [user_id, days])
            if activity_result:
                summary['total_activities'] = activity_result[0]['activity_count']
            
            summary['analysis_period_days'] = days
            summary['user_id'] = user_id
            
            return summary
                
        except Exception as e:
            raise ValueError(f"Failed to generate health summary: {str(e)}")
    
    @mcp.resource("file://health_data_guide")
    def health_data_guide() -> str:
        """Complete guide to understanding and querying Garmin health data.
        
        This resource provides all the information needed to understand the available
        health data and how to query it effectively.
        """
        return _get_health_data_guide()
    
    return mcp


def _get_table_description(table_name: str) -> str:
    """Get human-readable description for table."""
    descriptions = {
        "daily_health_metrics": "Daily health summaries including steps, sleep, heart rate, stress, and other key metrics",
        "timeseries": "High-frequency data like heart rate readings throughout the day, stress levels, body battery",
        "activities": "Individual workouts and physical activities with performance metrics",
        "sync_status": "System table tracking data synchronization status (usually not needed for health analysis)"
    }
    return descriptions.get(table_name, "Health data table")


def _get_health_data_guide() -> str:
    """Get comprehensive guide for health data analysis."""
    return '''
# Garmin Health Data Analysis Guide

## Quick Start
1. Use `explore_database_structure` first to see what data is available
2. Use `get_table_details` to understand specific tables
3. Use `execute_sql_query` for custom analysis or `get_health_summary` for quick overviews

## Main Data Tables

### daily_health_metrics
**WHAT**: Daily summaries of all health metrics
**CONTAINS**: steps, sleep hours, heart rate averages, stress levels, body battery
**COMMON QUERIES**: 
- Recent trends: `SELECT metric_date, total_steps, sleep_duration_hours FROM daily_health_metrics WHERE user_id = 1 ORDER BY metric_date DESC LIMIT 30`
- Sleep analysis: `SELECT metric_date, sleep_duration_hours, deep_sleep_hours FROM daily_health_metrics WHERE sleep_duration_hours IS NOT NULL`

### activities
**WHAT**: Individual workouts and physical activities
**CONTAINS**: activity type, duration, heart rate, training load
**COMMON QUERIES**:
- Recent workouts: `SELECT activity_date, activity_name, duration_seconds/60 as minutes FROM activities ORDER BY activity_date DESC`
- Performance trends: `SELECT activity_name, AVG(avg_heart_rate), AVG(training_load) FROM activities GROUP BY activity_name`

### timeseries
**WHAT**: High-frequency data throughout the day
**CONTAINS**: heart rate readings, stress measurements, body battery levels with timestamps
**USE CASE**: Detailed intraday analysis

## Health Metrics Available
- **Steps & Movement**: total_steps, total_distance_meters
- **Sleep**: sleep_duration_hours, deep_sleep_hours, rem_sleep_hours
- **Heart Rate**: resting_heart_rate, max_heart_rate, average_heart_rate
- **Stress & Recovery**: avg_stress_level, body_battery_high/low
- **Training**: training_readiness_score, activities data

## Tips for Analysis
- Always include `user_id = 1` in WHERE clauses
- Use `metric_date` for date filtering in daily_health_metrics
- Use `activity_date` for date filtering in activities
- NULL values are common - use `IS NOT NULL` to filter out missing data
- For recent data: `WHERE metric_date >= date('now', '-30 days')`

## Common Analysis Patterns
1. **Trend Analysis**: Compare metrics over time periods
2. **Correlation Analysis**: Look for relationships between sleep, stress, and performance
3. **Goal Tracking**: Monitor progress toward targets (steps, sleep duration)
4. **Activity Analysis**: Understand workout patterns and performance
        '''.strip()


# Legacy function for backwards compatibility
def create_mcp_server_from_env() -> FastMCP:
    """Create MCP server from environment variables (backwards compatibility)."""
    return create_mcp_server()


# Main entry point for MCP server
def main():
    """Main entry point for the Garmin LocalDB MCP server."""
    try:
        mcp = create_mcp_server()
        mcp.run()
    except Exception as e:
        print(f"Failed to start MCP server: {e}")
        raise


if __name__ == "__main__":
    main()