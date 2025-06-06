#!/usr/bin/env python3
"""MCP Server for Garmin LocalDB integration."""

import asyncio
import json
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from sqlalchemy import text, inspect

from ..localdb import LocalDBClient

logger = logging.getLogger(__name__)


class GarmyMCPServer:
    """MCP server with LocalDB SQL access for Claude Desktop."""
    
    def __init__(self, db_path: Path):
        self.mcp = FastMCP("garmy-localdb")
        self.db_path = db_path
        self.localdb = LocalDBClient(db_path)
        
        self._register_tools()
        self._register_resources()
        self._register_prompts()
    
    def _register_tools(self):
        """Register all MCP tools."""
        
        @self.mcp.tool()
        def get_database_schema() -> Dict[str, Any]:
            """Get complete database schema with tables, columns, and relationships."""
            inspector = inspect(self.localdb.storage.engine)
            
            schema = {"tables": {}, "semantics": {}}
            
            # Get all tables
            for table_name in inspector.get_table_names():
                columns = inspector.get_columns(table_name)
                indexes = inspector.get_indexes(table_name)
                foreign_keys = inspector.get_foreign_keys(table_name)
                
                schema["tables"][table_name] = {
                    "columns": [
                        {
                            "name": col["name"],
                            "type": str(col["type"]),
                            "nullable": col["nullable"],
                            "primary_key": col.get("primary_key", False),
                            "autoincrement": col.get("autoincrement", False)
                        }
                        for col in columns
                    ],
                    "indexes": [
                        {
                            "name": idx["name"],
                            "columns": idx["column_names"],
                            "unique": idx["unique"]
                        }
                        for idx in indexes
                    ],
                    "foreign_keys": [
                        {
                            "columns": fk["constrained_columns"],
                            "refers_to": f"{fk['referred_table']}.{fk['referred_columns']}"
                        }
                        for fk in foreign_keys
                    ]
                }
            
            # Add semantic information
            schema["semantics"] = {
                "users": "User accounts and profile information",
                "steps_data": "Daily step counts, distances, and step goals",
                "heart_rate_data": "Heart rate summaries with min/max/avg/resting values",
                "sleep_data": "Sleep duration, efficiency, and phase breakdowns",
                "body_battery_data": "Body battery energy levels and charging/draining periods",
                "activities_data": "Exercise activities with performance metrics (JSON format)",
                "calories_data": "Daily calorie intake and burn information",
                "training_readiness_data": "Training readiness scores and recovery metrics",
                
                "key_relationships": [
                    "All *_data tables link to users via user_id",
                    "Most tables use (user_id, data_date) as composite primary key",
                    "activities_data uses (user_id, activity_id) as primary key",
                    "JSON fields in activities_data contain detailed activity metrics"
                ],
                
                "common_queries": [
                    "JOIN tables on user_id for multi-metric analysis",
                    "Filter by data_date ranges for time series analysis",
                    "Use JSON_EXTRACT for activities_data details",
                    "GROUP BY data_date for daily aggregations"
                ]
            }
            
            return schema
        
        @self.mcp.tool()
        def execute_sql(query: str) -> Dict[str, Any]:
            """Execute read-only SQL query against LocalDB.
            
            Security: Only SELECT statements are allowed.
            Access: Full read access to all LocalDB tables.
            
            Args:
                query: SQL SELECT query to execute
                
            Returns:
                Query results with columns and rows
            """
            # Comprehensive security validation
            query_clean = query.strip()
            
            # Remove comments and normalize
            lines = []
            for line in query_clean.split('\n'):
                # Remove SQL comments
                if '--' in line:
                    line = line[:line.index('--')]
                lines.append(line)
            query_clean = ' '.join(lines).strip()
            
            # Check for dangerous keywords (case insensitive)
            dangerous_keywords = [
                'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 
                'TRUNCATE', 'REPLACE', 'EXEC', 'EXECUTE', 'CALL',
                'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK'
            ]
            
            query_upper = query_clean.upper()
            for keyword in dangerous_keywords:
                if keyword in query_upper:
                    return {
                        "error": f"Forbidden keyword '{keyword}' detected. Only SELECT queries are allowed.",
                        "help": "Use SELECT statements to query data. Examples: SELECT * FROM users; SELECT COUNT(*) FROM steps_data WHERE user_id = 'user123';"
                    }
            
            # Must start with SELECT
            if not query_upper.startswith('SELECT'):
                return {
                    "error": "Query must start with SELECT for security reasons.",
                    "help": "Examples: SELECT * FROM users; SELECT data_date, total_steps FROM steps_data LIMIT 10;"
                }
            
            try:
                with self.localdb.storage.get_session() as session:
                    result = session.execute(text(query))
                    
                    # Handle different result types
                    if result.returns_rows:
                        columns = list(result.keys()) if result.keys() else []
                        rows = result.fetchall()
                        
                        # Convert rows to dictionaries with proper serialization
                        formatted_rows = []
                        for row in rows:
                            row_dict = {}
                            for i, col_name in enumerate(columns):
                                value = row[i]
                                # Handle datetime serialization
                                if isinstance(value, (datetime, date)):
                                    row_dict[col_name] = value.isoformat()
                                else:
                                    row_dict[col_name] = value
                            formatted_rows.append(row_dict)
                        
                        return {
                            "success": True,
                            "columns": columns,
                            "rows": formatted_rows,
                            "row_count": len(formatted_rows),
                            "query_executed": query
                        }
                    else:
                        # Handle non-returning queries (shouldn't happen with SELECT only)
                        return {
                            "success": True,
                            "message": "Query executed successfully (no rows returned)",
                            "query_executed": query
                        }
                        
            except Exception as e:
                error_msg = str(e)
                
                # Provide helpful error messages
                if "no such table" in error_msg.lower():
                    return {
                        "error": f"Table not found: {error_msg}",
                        "help": "Use get_database_schema() to see available tables",
                        "query_attempted": query
                    }
                elif "no such column" in error_msg.lower():
                    return {
                        "error": f"Column not found: {error_msg}",
                        "help": "Use get_database_schema() to see available columns for each table",
                        "query_attempted": query
                    }
                else:
                    return {
                        "error": f"SQL execution failed: {error_msg}",
                        "query_attempted": query
                    }
        
        @self.mcp.tool()
        def get_user_summary(user_id: str) -> Dict[str, Any]:
            """Get comprehensive summary for a specific user including stats and recent data."""
            user = self.localdb.get_user(user_id)
            if not user:
                return {"error": f"User {user_id} not found"}
            
            # Get available metrics
            metrics = self.localdb.list_user_metrics(user_id)
            
            summary = {
                "user_info": user,
                "available_metrics": metrics,
                "metrics_summary": {},
                "recent_data_samples": {}
            }
            
            # Get stats for each metric
            for metric in metrics:
                try:
                    metric_stats = self.localdb.get_metric_stats(user_id, metric)
                    summary["metrics_summary"][metric] = metric_stats
                    
                    # Get recent sample data (last 3 records)
                    with self.localdb.storage.get_session() as session:
                        # Use auto-detection instead of hardcoded mapping
                        inspector = inspect(session.bind)
                        available_tables = inspector.get_table_names()
                        expected_table = f"{metric}_data"
                        
                        if expected_table in available_tables:
                            table_name = expected_table
                            if metric == 'activities':
                                sample_query = f"""
                                    SELECT * FROM {table_name} 
                                    WHERE user_id = '{user_id}' 
                                    ORDER BY activity_date DESC 
                                    LIMIT 3
                                """
                            else:
                                sample_query = f"""
                                    SELECT * FROM {table_name} 
                                    WHERE user_id = '{user_id}' 
                                    ORDER BY data_date DESC 
                                    LIMIT 3
                                """
                            result = session.execute(text(sample_query))
                            sample_rows = [dict(row._mapping) for row in result.fetchall()]
                            
                            # Serialize dates
                            for row in sample_rows:
                                for key, value in row.items():
                                    if isinstance(value, (datetime, date)):
                                        row[key] = value.isoformat()
                            
                            summary["recent_data_samples"][metric] = sample_rows
                            
                except Exception as e:
                    summary["metrics_summary"][metric] = {"error": str(e)}
            
            return summary
        
        @self.mcp.tool()
        def list_all_users() -> Dict[str, Any]:
            """List all users with basic statistics."""
            users = self.localdb.list_users()
            
            # Enhance with quick stats
            for user in users:
                user_id = user['user_id']
                metrics = self.localdb.list_user_metrics(user_id)
                user['available_metrics'] = metrics
                user['metrics_count'] = len(metrics)
            
            return {
                "users": users,
                "total_count": len(users)
            }
        
        @self.mcp.tool()
        def get_database_stats() -> Dict[str, Any]:
            """Get overall database statistics and health."""
            stats = self.localdb.get_database_stats()
            
            # Add file size info
            try:
                db_size = self.db_path.stat().st_size
                stats['database_file'] = {
                    'path': str(self.db_path),
                    'size_bytes': db_size,
                    'size_mb': round(db_size / 1024 / 1024, 2)
                }
            except Exception as e:
                stats['database_file'] = {'error': str(e)}
            
            return stats
        
        @self.mcp.tool()
        def sync_recent_data(user_id: str, days: int = 7) -> Dict[str, Any]:
            """Sync recent data for all available metrics for a user."""
            try:
                async def do_sync():
                    return await self.localdb.sync_recent_user_data(user_id, days)
                
                # Handle event loop properly
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # We're in an existing loop, use thread pool
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, do_sync())
                            return future.result(timeout=300)  # 5 minute timeout
                    else:
                        return asyncio.run(do_sync())
                except RuntimeError:
                    return asyncio.run(do_sync())
                    
            except Exception as e:
                return {
                    "error": f"Sync failed: {str(e)}",
                    "suggestion": "Check authentication and network connectivity"
                }
    
    def _register_resources(self):
        """Register MCP resources for structured data access."""
        
        @self.mcp.resource("schema://garmy-localdb")
        def get_schema_resource() -> str:
            """Database schema as a structured resource."""
            schema = get_database_schema()
            return json.dumps(schema, indent=2, default=str)
        
        @self.mcp.resource("users://all")  
        def get_users_resource() -> str:
            """All users as a structured resource."""
            users = list_all_users()
            return json.dumps(users, indent=2, default=str)
    
    def _register_prompts(self):
        """Register analysis prompts for common use cases."""
        
        @self.mcp.prompt()
        def analyze_health_trends(user_id: str, days: int = 30, focus: str = "overall") -> str:
            """Generate prompt for health trend analysis.
            
            Args:
                user_id: Target user ID
                days: Number of recent days to analyze  
                focus: Analysis focus (sleep, activity, heart_rate, body_battery, overall)
            """
            
            return f"""
# Health Trends Analysis for User {user_id}

Analyze the last {days} days of health data for user {user_id} with focus on: **{focus}**

## Getting Started
1. First, get user info: `get_user_summary("{user_id}")`
2. Check database schema: `get_database_schema()`

## Focus Areas by Type:

### Overall Analysis
- Cross-metric correlations (sleep quality vs body battery, steps vs heart rate)
- Weekly patterns and trends
- Goal achievement rates
- Data completeness assessment

### Sleep Analysis  
```sql
SELECT data_date, sleep_time_seconds/3600 as sleep_hours, 
       deep_sleep_seconds/3600 as deep_hours,
       sleep_efficiency_percentage as efficiency
FROM sleep_data 
WHERE user_id = '{user_id}' 
AND data_date >= date('now', '-{days} days')
ORDER BY data_date;
```

### Activity Analysis
```sql  
SELECT data_date, total_steps, step_goal,
       total_distance/1000 as distance_km,
       CASE WHEN total_steps >= step_goal THEN 1 ELSE 0 END as goal_met
FROM steps_data
WHERE user_id = '{user_id}'
AND data_date >= date('now', '-{days} days')
ORDER BY data_date;
```

### Heart Rate Analysis
```sql
SELECT data_date, resting_heart_rate, max_heart_rate,
       max_heart_rate - resting_heart_rate as hr_range
FROM heart_rate_data
WHERE user_id = '{user_id}'  
AND data_date >= date('now', '-{days} days')
ORDER BY data_date;
```

### Body Battery Analysis
```sql
SELECT data_date, start_level, end_level, net_change,
       charging_periods_count, draining_periods_count
FROM body_battery_data
WHERE user_id = '{user_id}'
AND data_date >= date('now', '-{days} days') 
ORDER BY data_date;
```

## Analysis Guidelines
- Look for patterns, trends, and anomalies
- Calculate averages and ranges  
- Identify correlations between metrics
- Note data gaps or quality issues
- Provide actionable insights
- Use visualizable data formats where helpful

Start your analysis now using the SQL queries above and the available tools.
            """.strip()
        
        @self.mcp.prompt()
        def explore_activities(user_id: str, activity_type: str = "all", limit: int = 20) -> str:
            """Generate prompt for activity exploration.
            
            Args:
                user_id: Target user ID
                activity_type: Filter by activity type or "all"
                limit: Maximum activities to analyze
            """
            
            activity_filter = ""
            if activity_type != "all":
                activity_filter = f"AND JSON_EXTRACT(activity_data, '$.activity_type.typeKey') = '{activity_type}'"
            
            return f"""
# Activity Analysis for User {user_id}

Explore and analyze activity data for user {user_id} focusing on: **{activity_type}**

## Start Here
1. Get user overview: `get_user_summary("{user_id}")`
2. Check available activities:

```sql
SELECT activity_date, activity_id,
       JSON_EXTRACT(activity_data, '$.activity_name') as name,
       JSON_EXTRACT(activity_data, '$.activity_type.typeKey') as type,
       JSON_EXTRACT(activity_data, '$.duration') as duration_seconds,
       JSON_EXTRACT(activity_data, '$.average_hr') as avg_hr
FROM activities_data
WHERE user_id = '{user_id}' {activity_filter}
ORDER BY activity_date DESC
LIMIT {limit};
```

## Deep Dive Queries

### Activity Types Distribution
```sql
SELECT JSON_EXTRACT(activity_data, '$.activity_type.typeKey') as activity_type,
       COUNT(*) as count,
       AVG(JSON_EXTRACT(activity_data, '$.duration')/60) as avg_duration_min
FROM activities_data  
WHERE user_id = '{user_id}'
GROUP BY activity_type
ORDER BY count DESC;
```

### Performance Metrics
```sql
SELECT activity_date,
       JSON_EXTRACT(activity_data, '$.activity_name') as name,
       JSON_EXTRACT(activity_data, '$.duration')/60 as duration_min,
       JSON_EXTRACT(activity_data, '$.average_hr') as avg_hr,
       JSON_EXTRACT(activity_data, '$.max_hr') as max_hr,
       JSON_EXTRACT(activity_data, '$.aerobic_training_effect') as aerobic_te
FROM activities_data
WHERE user_id = '{user_id}' {activity_filter}
AND JSON_EXTRACT(activity_data, '$.duration') > 0
ORDER BY activity_date DESC
LIMIT {limit};
```

### Weekly Activity Patterns  
```sql
SELECT strftime('%w', activity_date) as day_of_week,
       COUNT(*) as activity_count,
       AVG(JSON_EXTRACT(activity_data, '$.duration')/60) as avg_duration
FROM activities_data
WHERE user_id = '{user_id}' {activity_filter}
GROUP BY day_of_week
ORDER BY day_of_week;
```

## Analysis Focus
- Activity frequency and consistency
- Performance trends over time  
- Heart rate patterns during exercise
- Training load and recovery
- Activity type preferences
- Duration and intensity patterns

Explore the data using these queries and provide insights about the user's activity patterns.
            """.strip()
    
    def run(self):
        """Run the MCP server."""
        return self.mcp.run()


def create_server(db_path: str = None) -> GarmyMCPServer:
    """Create and return MCP server instance."""
    if db_path is None:
        db_path = Path.home() / '.garmy' / 'localdb.db'
    else:
        db_path = Path(db_path)
    
    return GarmyMCPServer(db_path)


def main():
    """Main entry point for MCP server."""
    # Handle help requests
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        print("""
Garmy LocalDB MCP Server

Usage:
    python -m garmy.mcp [DB_PATH]
    
Arguments:
    DB_PATH     Path to LocalDB database file (optional)
                Default: ~/.garmy/localdb.db
                Can also be set via GARMY_DB_PATH environment variable

Environment Variables:
    GARMY_DB_PATH    Path to LocalDB database file

Examples:
    python -m garmy.mcp
    python -m garmy.mcp /path/to/custom.db
    GARMY_DB_PATH=/path/to/db.db python -m garmy.mcp

The MCP server provides SQL access to Garmin health data stored in LocalDB
for integration with Claude Desktop and other MCP clients.
        """.strip())
        sys.exit(0)
    
    # Setup logging for development
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting Garmy LocalDB MCP Server...")
    
    # Get database path from environment or command line
    db_path = os.getenv('GARMY_DB_PATH')
    if not db_path and len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    if db_path:
        logger.info(f"Using database path: {db_path}")
    else:
        logger.info("Using default database path: ~/.garmy/localdb.db")
    
    try:
        # Create and run server
        server = create_server(db_path)
        logger.info("MCP Server initialized successfully")
        server.run()
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()