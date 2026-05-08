"""Garmin LocalDB MCP Server implementation.

Provides secure, read-only access to synchronized Garmin health data
through the Model Context Protocol with optimized tools for LLM understanding.
Optionally supports syncing data from Garmin Connect when enabled.
"""

import logging
import os
import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from fastmcp import FastMCP
except ImportError:
    raise ImportError(
        "FastMCP is required for MCP server functionality. "
        "Install with: pip install garmy[mcp] or pip install fastmcp"
    )

from ..localdb.models import MetricType
from .config import MCPConfig


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

    ALLOWED_STATEMENTS = ("select", "with")
    FORBIDDEN_KEYWORDS = {
        "insert",
        "update",
        "delete",
        "drop",
        "create",
        "alter",
        "pragma",
        "attach",
        "detach",
        "vacuum",
        "analyze",
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
            allowed = ", ".join(cls.ALLOWED_STATEMENTS).upper()
            raise ValueError(f"Only {allowed} queries are allowed for security")

        # Check for forbidden keywords
        query_words = set(re.findall(r"\\b\\w+\\b", query_lower))
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
            elif char == ";" and not in_single_quote and not in_double_quote:
                return True

        return False

    @staticmethod
    def add_row_limit(query: str, limit: int = 1000) -> str:
        """Add LIMIT clause if not present."""
        query_lower = query.lower()
        if "limit" not in query_lower:
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
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def get_connection(self):
        """Get read-only database connection."""
        return SQLiteConnection(self.config.db_path)

    def execute_safe_query(
        self, query: str, params: Optional[List[Any]] = None
    ) -> List[Dict[str, Any]]:
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
        if "GARMY_DB_PATH" not in os.environ:
            raise ValueError("GARMY_DB_PATH environment variable must be set")

        db_path = Path(os.environ["GARMY_DB_PATH"])
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
            table_names = [row["name"] for row in tables]

            # Get row counts for each table
            table_info = {}
            for table_name in table_names:
                count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                count_result = db_manager.execute_safe_query(count_query)

                table_info[table_name] = {
                    "row_count": count_result[0]["count"],
                    "description": _get_table_description(table_name),
                }

            return {
                "available_tables": table_info,
                "metric_types": [mt.value for mt in MetricType],
                "usage_tip": "Use 'execute_sql_query' to get specific data from any table, or 'get_table_details' to see column structure",
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
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
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
                table_list = [row["name"] for row in available_tables]
                raise ValueError(
                    f"Table '{table_name}' does not exist. Available tables: {', '.join(table_list)}"
                )

            # Get table schema using PRAGMA
            schema_query = f"PRAGMA table_info({table_name})"
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(schema_query)
                columns = cursor.fetchall()

            column_info = [
                {
                    "name": col[1],
                    "type": col[2],
                    "required": bool(col[3]),
                    "is_primary_key": bool(col[5]),
                }
                for col in columns
            ]

            # Get sample data (latest 3 records)
            sample_query = f"SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT 3"
            sample_data = db_manager.execute_safe_query(sample_query)

            return {
                "table_name": table_name,
                "columns": column_info,
                "sample_data": sample_data,
                "description": _get_table_description(table_name),
                "usage_tip": f"Use 'execute_sql_query' with SELECT statements to get specific data from {table_name}",
            }

        except Exception as e:
            raise ValueError(f"Failed to get table details: {str(e)}")

    @mcp.tool()
    def execute_sql_query(
        query: str, params: Optional[List[Any]] = None
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
        - Timeseries data (timestamp is epoch ms): "SELECT datetime(timestamp/1000, 'unixepoch', 'localtime') as ts, value FROM timeseries WHERE metric_type = 'heart_rate' AND timestamp/1000 BETWEEN unixepoch('2026-01-01', 'localtime') AND unixepoch('2026-01-02', 'localtime')"

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
    def get_health_summary(user_id: int = 1, days: int = 30) -> Dict[str, Any]:
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

            summary_result = db_manager.execute_safe_query(
                summary_query, [user_id, days]
            )
            summary = summary_result[0] if summary_result else {}

            # Get activity count
            activity_query = """
                SELECT COUNT(*) as activity_count
                FROM activities 
                WHERE user_id = ? 
                AND activity_date >= date('now', '-' || ? || ' days')
            """

            activity_result = db_manager.execute_safe_query(
                activity_query, [user_id, days]
            )
            if activity_result:
                summary["total_activities"] = activity_result[0]["activity_count"]

            summary["analysis_period_days"] = days
            summary["user_id"] = user_id

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

    # Only add sync tool if sync is enabled
    if config.enable_sync:
        _register_sync_tool(mcp, config)

    # Only add workout tools if workouts are enabled
    if config.enable_workouts:
        _register_workout_tools(mcp, config)

    return mcp


def _register_sync_tool(mcp: FastMCP, config: MCPConfig) -> None:
    """Register the sync tool with the MCP server.

    Args:
        mcp: The FastMCP server instance
        config: MCP configuration with sync settings
    """
    from ..localdb.config import LocalDBConfig
    from ..localdb.progress import ProgressReporter
    from ..localdb.sync import SyncManager

    # Create a simple progress reporter that collects messages
    class MCPProgressReporter(ProgressReporter):
        """Progress reporter that collects messages for MCP response."""

        def __init__(self):
            super().__init__(use_tqdm=False)
            self.messages: List[str] = []

        def info(self, message: str) -> None:
            self.messages.append(f"[INFO] {message}")

        def warning(self, message: str) -> None:
            self.messages.append(f"[WARNING] {message}")

        def error(self, message: str) -> None:
            self.messages.append(f"[ERROR] {message}")

        def task_complete(self, metric: str, sync_date: date) -> None:
            pass  # Don't log individual task completions to reduce noise

        def task_failed(self, metric: str, sync_date: date) -> None:
            self.messages.append(f"[FAILED] {metric} for {sync_date}")

        def task_skipped(self, metric: str, sync_date: date) -> None:
            pass  # Don't log skips to reduce noise

    @mcp.tool()
    def sync_health_data(
        last_days: int = 7,
        metrics: Optional[str] = None,
        user_id: int = 1,
        resync_days: int = 0,
    ) -> Dict[str, Any]:
        """WHEN TO USE: When you need to fetch fresh data from Garmin Connect.

        This tool syncs health data from Garmin Connect API to the local database.
        Use this when you need the latest data that may not be in the database yet.

        IMPORTANT: Requires valid saved authentication tokens. Will fail if tokens
        are expired or missing - user must run 'garmy-sync sync' manually first to
        authenticate.

        Args:
            last_days: Number of days to sync, counting back from today (default: 7, max: 30)
            metrics: Comma-separated list of metrics to sync (default: all).
                     Available: DAILY_SUMMARY, SLEEP, HEART_RATE, STEPS, STRESS,
                     BODY_BATTERY, HRV, CALORIES, RESPIRATION, TRAINING_READINESS,
                     ACTIVITIES, BODY_COMPOSITION, SPO2, RESTING_HEART_RATE,
                     INTENSITY_MINUTES, FLOORS, TRAINING_STATUS, ENDURANCE_SCORE,
                     HEALTH_SNAPSHOT
            user_id: User ID for database records (default: 1)
            resync_days: Force re-sync of the last N days even if already completed.
                         Useful for updating partial data from earlier syncs (default: 0, max: 7)

        Returns:
            Sync statistics including completed, skipped, and failed counts
        """
        # Validate parameters
        if last_days < 1:
            raise ValueError("last_days must be at least 1")
        if last_days > 30:
            raise ValueError(
                "last_days cannot exceed 30 for MCP sync. "
                "For larger syncs, use 'garmy-sync sync' CLI directly."
            )
        if user_id < 1:
            raise ValueError("user_id must be positive")
        if resync_days < 0:
            raise ValueError("resync_days must be non-negative")
        if resync_days > 7:
            raise ValueError(
                "resync_days cannot exceed 7 for MCP sync. "
                "For larger re-syncs, use 'garmy-sync sync' CLI directly."
            )

        # Parse metrics if provided
        sync_metrics: Optional[List[MetricType]] = None
        if metrics:
            sync_metrics = []
            for name in metrics.split(","):
                name = name.strip().upper()
                try:
                    sync_metrics.append(MetricType[name])
                except KeyError:
                    available = ", ".join([m.name for m in MetricType])
                    raise ValueError(f"Invalid metric: {name}. Available: {available}")

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=last_days - 1)

        # Create progress reporter
        progress = MCPProgressReporter()

        try:
            # Initialize sync manager
            localdb_config = LocalDBConfig()
            manager = SyncManager(
                db_path=config.db_path,
                config=localdb_config,
                progress_reporter=progress,
                token_dir=config.token_dir,
            )

            # Initialize with saved tokens only (no interactive prompts)
            try:
                manager.initialize()
            except RuntimeError as e:
                return {
                    "success": False,
                    "error": "Authentication required",
                    "message": (
                        "No valid saved tokens found. Please run "
                        "'garmy-sync sync' from the command line first to authenticate, "
                        "then try again."
                    ),
                    "details": str(e),
                }

            # Execute sync
            stats = manager.sync_range(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                metrics=sync_metrics,
                resync_days=resync_days,
            )

            return {
                "success": True,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "statistics": {
                    "completed": stats["completed"],
                    "skipped": stats["skipped"],
                    "failed": stats["failed"],
                    "total_tasks": stats["total_tasks"],
                },
                "metrics_synced": (
                    [m.name for m in sync_metrics]
                    if sync_metrics
                    else [m.name for m in MetricType]
                ),
                "messages": progress.messages[-10:],  # Last 10 messages
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "messages": progress.messages[-10:],
            }


def _register_workout_tools(mcp: FastMCP, config: MCPConfig) -> None:
    """Register workout management tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        config: MCP configuration with workout settings
    """
    from ..auth.client import AuthClient
    from ..core.client import APIClient
    from ..workouts import SportType, WorkoutBuilder
    from ..workouts.exercises import (
        resolve_exercise,
        search_exercises as search_exercises_func,
    )

    def _get_authenticated_client() -> APIClient:
        """Get an authenticated API client using saved tokens."""
        auth_client = AuthClient(token_dir=config.token_dir)
        if not auth_client.is_authenticated:
            if auth_client.needs_refresh:
                auth_client.refresh_tokens()
            else:
                raise ValueError(
                    "Authentication required. Please run 'garmy-sync sync' from the "
                    "command line first to authenticate, then try again."
                )
        return APIClient(auth_client=auth_client)

    @mcp.tool()
    def list_workouts(
        limit: int = 20,
        my_workouts_only: bool = True,
    ) -> Dict[str, Any]:
        """WHEN TO USE: When you need to see existing workouts in Garmin Connect.

        Lists workouts from the user's Garmin Connect account. Use this to see
        what workouts are available before modifying or scheduling them.

        IMPORTANT: Requires valid saved authentication tokens.

        Args:
            limit: Maximum number of workouts to return (default: 20, max: 100)
            my_workouts_only: If True, only return user's own workouts (default: True)

        Returns:
            List of workouts with their IDs, names, sport types, and step counts
        """
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        try:
            api = _get_authenticated_client()
            workouts = api.workouts.list_workouts(
                limit=limit, my_workouts_only=my_workouts_only
            )

            return {
                "success": True,
                "count": len(workouts),
                "workouts": [
                    {
                        "workout_id": w.workout_id,
                        "name": w.name,
                        "sport_type": w.sport_type.key,
                        "description": w.description,
                        "step_count": len(w.steps),
                    }
                    for w in workouts
                ],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def get_workout(workout_id: int) -> Dict[str, Any]:
        """WHEN TO USE: When you need details about a specific workout.

        Gets the full details of a workout including all steps, targets, and durations.

        IMPORTANT: Requires valid saved authentication tokens.

        Args:
            workout_id: The Garmin workout ID to retrieve

        Returns:
            Full workout details including steps and structure.
            Repeat steps include a "skip_last_rest" boolean field indicating
            whether the last iteration skips its rest/recovery step.
        """
        if workout_id < 1:
            raise ValueError("workout_id must be positive")

        try:
            api = _get_authenticated_client()
            workout = api.workouts.get_workout(workout_id)

            if workout is None:
                return {"success": False, "error": f"Workout {workout_id} not found"}

            # Format steps for readability
            steps_info = []
            for i, step in enumerate(workout.steps):
                from ..workouts.models import RepeatGroup

                if isinstance(step, RepeatGroup):
                    from ..workouts.constants import EndConditionType

                    def format_nested_step(s):
                        """Format a nested step with appropriate field names."""
                        result = {
                            "type": s.step_type.value,
                            "end_condition": s.end_condition.condition_type.value,
                            "target_type": s.target.target_type.value,
                            "exercise_name": s.exercise_name,
                            "exercise_category": s.exercise_category,
                            "weight_value": s.weight_value,
                            "weight_unit": s.weight_unit,
                            "description": s.description,
                        }
                        # Use appropriate field name based on end condition type
                        if s.end_condition.condition_type == EndConditionType.REPS:
                            result["reps"] = (
                                int(s.end_condition.value)
                                if s.end_condition.value
                                else None
                            )
                        else:
                            result["duration_seconds"] = s.end_condition.value
                        return result

                    steps_info.append(
                        {
                            "index": i + 1,
                            "type": "repeat",
                            "iterations": step.iterations,
                            "skip_last_rest": step.smart_repeat,
                            "steps": [format_nested_step(s) for s in step.steps],
                        }
                    )
                else:
                    from ..workouts.constants import EndConditionType

                    step_info = {
                        "index": i + 1,
                        "type": step.step_type.value,
                        "end_condition": step.end_condition.condition_type.value,
                        "target_type": step.target.target_type.value,
                        "target_low": step.target.value_low,
                        "target_high": step.target.value_high,
                        "exercise_name": step.exercise_name,
                        "exercise_category": step.exercise_category,
                        "weight_value": step.weight_value,
                        "weight_unit": step.weight_unit,
                        "description": step.description,
                    }
                    # Use appropriate field name based on end condition type
                    if step.end_condition.condition_type == EndConditionType.REPS:
                        step_info["reps"] = (
                            int(step.end_condition.value)
                            if step.end_condition.value
                            else None
                        )
                    else:
                        step_info["duration_seconds"] = step.end_condition.value
                    steps_info.append(step_info)

            return {
                "success": True,
                "workout": {
                    "workout_id": workout.workout_id,
                    "name": workout.name,
                    "sport_type": workout.sport_type.key,
                    "description": workout.description,
                    "steps": steps_info,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def create_workout(
        name: str,
        sport_type: str = "cycling",
        description: Optional[str] = None,
        steps_json: Union[str, List[Dict[str, Any]], None] = None,
    ) -> Dict[str, Any]:
        """WHEN TO USE: When you need to create a new workout in Garmin Connect.

        Creates a structured workout that can be synced to Garmin devices.

        IMPORTANT: Requires valid saved authentication tokens.

        Args:
            name: Name for the workout
            sport_type: Sport type (cycling, running, swimming, strength_training, etc.)
            description: Optional description
            steps_json: JSON string defining workout steps.

        Step format - each step can have these fields:
            - type: "warmup", "interval", "recovery", "cooldown", "rest", or "repeat"
            - Duration (pick ONE): "seconds", "minutes", "duration_seconds", OR "reps"
            - reps: Number of repetitions (REQUIRED for strength exercises to show "Target: X Reps")
            - exercise_name: Exercise name (auto-resolved, e.g., "bench press" -> "BARBELL_BENCH_PRESS")
            - exercise_category: Optional category override
            - weight_value: Weight amount for strength exercises
            - weight_unit: "pound" or "kilogram" (default: pound)
            - target_power: [low, high] percentage of FTP for cycling
            - target_hr: [low, high] percentage of max HR
            - target_cadence: [low, high] RPM
            - description: Step description text
            - lap_button: true to end step on lap button press (default if no duration/reps specified)

        For repeats:
            - type: "repeat"
            - iterations: Number of times to repeat (e.g., 3)
            - skip_last_rest: When true, the last iteration skips its rest/recovery step.
              This avoids double-resting when a transition rest follows the repeat block.
              Recommended for strength training. (default: false)
            - steps: Array of steps to repeat

        IMPORTANT FOR STRENGTH TRAINING:
            - You MUST include "reps" to set the rep count (e.g., "reps": 10)
            - Without "reps", the step defaults to "lap button" end condition
            - The "reps" value is what shows as "Target: X Reps" in Garmin Connect UI
            - Use "skip_last_rest": true on repeat blocks to avoid double rest periods

        Example cycling workout:
            '[{"type": "warmup", "seconds": 300},
              {"type": "repeat", "iterations": 3, "steps": [
                {"type": "interval", "duration_seconds": 30, "target_power": [90, 95]},
                {"type": "rest", "duration_seconds": 60}
              ]},
              {"type": "cooldown", "minutes": 5}]'

        Example strength workout (note: reps is REQUIRED for rep-based exercises):
            '[{"type": "repeat", "iterations": 3, "skip_last_rest": true, "steps": [
                {"type": "interval", "reps": 10,
                 "exercise_name": "barbell bench press", "weight_value": 185, "weight_unit": "pound"},
                {"type": "rest", "seconds": 60}
              ]}]'

        Returns:
            Created workout details including the new workout_id
        """
        import json

        # Validate sport type
        try:
            sport = SportType.from_key(sport_type.lower())
        except (ValueError, AttributeError) as e:
            available = [s.key for s in SportType]
            raise ValueError(
                f"Invalid sport_type: {sport_type}. Available: {', '.join(available)}"
            ) from e

        try:
            api = _get_authenticated_client()
            builder = WorkoutBuilder(name, sport)

            if description:
                builder.with_description(description)

            # Parse and add steps if provided
            if steps_json:
                if isinstance(steps_json, str):
                    try:
                        steps = json.loads(steps_json)
                    except json.JSONDecodeError as e:
                        return {
                            "success": False,
                            "error": f"Invalid steps_json format: {e}",
                        }
                elif isinstance(steps_json, list):
                    # Handle case where environment already parsed the JSON
                    steps = steps_json
                else:
                    return {
                        "success": False,
                        "error": f"steps_json must be a JSON string or list, got {type(steps_json).__name__}",
                    }

                _add_steps_from_json(builder, steps)

            workout = builder.build()
            result = api.workouts.create_workout(workout)

            return {
                "success": True,
                "message": f"Workout '{name}' created successfully",
                "workout": {
                    "workout_id": result.workout_id,
                    "name": result.name,
                    # Use the sport type we requested, not from response
                    # (Garmin returns sportTypeKey=null when we only send sportTypeKey)
                    "sport_type": sport.key,
                },
            }
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid steps_json format: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def schedule_workout(
        workout_id: int,
        date: str,
    ) -> Dict[str, Any]:
        """WHEN TO USE: When you need to schedule a workout for a specific date.

        Schedules an existing workout to appear on the user's Garmin calendar
        for the specified date. The workout will sync to connected devices.

        IMPORTANT: Requires valid saved authentication tokens.

        Args:
            workout_id: The Garmin workout ID to schedule
            date: Date to schedule in YYYY-MM-DD format (e.g., "2024-01-15")

        Returns:
            Success status and confirmation message
        """
        import re

        if workout_id < 1:
            raise ValueError("workout_id must be positive")

        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            raise ValueError("date must be in YYYY-MM-DD format")

        try:
            api = _get_authenticated_client()
            api.workouts.schedule_workout(workout_id, date)

            return {
                "success": True,
                "message": f"Workout {workout_id} scheduled for {date}",
                "workout_id": workout_id,
                "scheduled_date": date,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def delete_workout(workout_id: int) -> Dict[str, Any]:
        """WHEN TO USE: When you need to delete a workout from Garmin Connect.

        Permanently deletes a workout. This cannot be undone.

        IMPORTANT: Requires valid saved authentication tokens.

        Args:
            workout_id: The Garmin workout ID to delete

        Returns:
            Success status and confirmation message
        """
        if workout_id < 1:
            raise ValueError("workout_id must be positive")

        try:
            api = _get_authenticated_client()
            api.workouts.delete_workout(workout_id)

            return {
                "success": True,
                "message": f"Workout {workout_id} deleted successfully",
                "workout_id": workout_id,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def search_exercises(
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """WHEN TO USE: When you need to find valid Garmin exercise names for strength workouts.

        Searches the exercise database to find matching exercises. Use this to discover
        the correct exercise name before creating a strength training workout.

        This tool does NOT require authentication - it's a local lookup.

        Args:
            query: Search term (e.g., "bench press", "curl", "squat")
            limit: Maximum results to return (default: 10, max: 50)
            category: Optional category filter (e.g., "BENCH_PRESS", "CURL", "SQUAT")

        Returns:
            List of matching exercises with their Garmin names, categories, and match scores
        """
        if limit < 1 or limit > 50:
            raise ValueError("limit must be between 1 and 50")

        try:
            results = search_exercises_func(query, limit=limit)

            # Filter by category if provided
            if category:
                category_upper = category.upper()
                results = [r for r in results if r.category == category_upper]

            return {
                "success": True,
                "query": query,
                "count": len(results),
                "exercises": [
                    {
                        "name": r.name,
                        "category": r.category,
                        "score": round(r.score, 3),
                    }
                    for r in results
                ],
                "usage_tip": "Use the 'name' field as exercise_name in create_workout steps_json",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _is_garmin_format(name: str) -> bool:
        """Check if name is already in SCREAMING_SNAKE_CASE Garmin format."""
        return name == name.upper() and "_" in name

    def _add_steps_from_json(builder: WorkoutBuilder, steps: list) -> None:
        """Add steps to builder from JSON structure."""
        for step in steps:
            step_type = step.get("type", "interval").lower()
            minutes = step.get("minutes")
            # Accept both "seconds" and "duration_seconds" for consistency with get_workout output
            seconds = step.get("seconds") or step.get("duration_seconds")
            distance_km = step.get("distance_km")
            target_power = step.get("target_power")
            target_hr = step.get("target_hr")
            target_cadence = step.get("target_cadence")
            description = step.get("description")
            lap_button = step.get("lap_button", False)

            # Extract exercise fields for strength training
            reps = step.get("reps")
            exercise_name = step.get("exercise_name")
            exercise_category = step.get("exercise_category")
            weight_value = step.get("weight_value")
            weight_unit = step.get("weight_unit")

            # Auto-resolve exercise name if not already in Garmin format
            if exercise_name and not _is_garmin_format(exercise_name):
                try:
                    resolved_name, resolved_category = resolve_exercise(exercise_name)
                    exercise_name = resolved_name
                    # Only override category if not explicitly provided
                    if not exercise_category:
                        exercise_category = resolved_category
                except ValueError:
                    # If resolution fails, pass through the original name
                    # Let Garmin API handle the error
                    pass

            # Convert target lists to tuples
            if target_power and isinstance(target_power, list):
                target_power = tuple(target_power)
            if target_hr and isinstance(target_hr, list):
                target_hr = tuple(target_hr)
            if target_cadence and isinstance(target_cadence, list):
                target_cadence = tuple(target_cadence)

            if step_type == "repeat":
                iterations = step.get("iterations", 1)
                skip_last_rest = step.get("skip_last_rest", False)
                repeat_steps = step.get("steps", [])
                repeat_builder = builder.repeat(iterations, smart_repeat=skip_last_rest)

                for rs in repeat_steps:
                    rs_type = rs.get("type", "interval").lower()
                    rs_minutes = rs.get("minutes")
                    # Accept both "seconds" and "duration_seconds"
                    rs_seconds = rs.get("seconds") or rs.get("duration_seconds")
                    rs_target_power = rs.get("target_power")
                    rs_target_hr = rs.get("target_hr")
                    rs_desc = rs.get("description")

                    # Extract exercise fields for nested steps
                    rs_reps = rs.get("reps")
                    rs_exercise_name = rs.get("exercise_name")
                    rs_exercise_category = rs.get("exercise_category")
                    rs_weight_value = rs.get("weight_value")
                    rs_weight_unit = rs.get("weight_unit")

                    # Auto-resolve exercise name if not already in Garmin format
                    if rs_exercise_name and not _is_garmin_format(rs_exercise_name):
                        try:
                            resolved_name, resolved_category = resolve_exercise(
                                rs_exercise_name
                            )
                            rs_exercise_name = resolved_name
                            # Only override category if not explicitly provided
                            if not rs_exercise_category:
                                rs_exercise_category = resolved_category
                        except ValueError:
                            # If resolution fails, pass through the original name
                            # Let Garmin API handle the error
                            pass

                    if rs_target_power and isinstance(rs_target_power, list):
                        rs_target_power = tuple(rs_target_power)
                    if rs_target_hr and isinstance(rs_target_hr, list):
                        rs_target_hr = tuple(rs_target_hr)

                    if rs_type == "interval":
                        repeat_builder.interval(
                            minutes=rs_minutes,
                            seconds=rs_seconds,
                            target_power=rs_target_power,
                            target_hr=rs_target_hr,
                            description=rs_desc,
                            reps=rs_reps,
                            exercise_name=rs_exercise_name,
                            exercise_category=rs_exercise_category,
                            weight_value=rs_weight_value,
                            weight_unit=rs_weight_unit,
                        )
                    elif rs_type == "recovery":
                        repeat_builder.recovery(
                            minutes=rs_minutes,
                            seconds=rs_seconds,
                            target_power=rs_target_power,
                            target_hr=rs_target_hr,
                            description=rs_desc,
                            reps=rs_reps,
                            exercise_name=rs_exercise_name,
                            exercise_category=rs_exercise_category,
                            weight_value=rs_weight_value,
                            weight_unit=rs_weight_unit,
                        )
                    elif rs_type == "rest":
                        repeat_builder.rest(
                            minutes=rs_minutes, seconds=rs_seconds, description=rs_desc
                        )

                repeat_builder.end_repeat()

            elif step_type == "warmup":
                builder.warmup(
                    minutes=minutes,
                    seconds=seconds,
                    distance_km=distance_km,
                    target_power=target_power,
                    target_hr=target_hr,
                    lap_button=lap_button,
                    description=description,
                )
            elif step_type == "cooldown":
                builder.cooldown(
                    minutes=minutes,
                    seconds=seconds,
                    distance_km=distance_km,
                    target_power=target_power,
                    target_hr=target_hr,
                    lap_button=lap_button,
                    description=description,
                )
            elif step_type == "interval":
                builder.interval(
                    minutes=minutes,
                    seconds=seconds,
                    distance_km=distance_km,
                    target_power=target_power,
                    target_hr=target_hr,
                    target_cadence=target_cadence,
                    lap_button=lap_button,
                    description=description,
                    reps=reps,
                    exercise_name=exercise_name,
                    exercise_category=exercise_category,
                    weight_value=weight_value,
                    weight_unit=weight_unit,
                )
            elif step_type == "recovery":
                builder.recovery(
                    minutes=minutes,
                    seconds=seconds,
                    distance_km=distance_km,
                    target_power=target_power,
                    target_hr=target_hr,
                    lap_button=lap_button,
                    description=description,
                    reps=reps,
                    exercise_name=exercise_name,
                    exercise_category=exercise_category,
                    weight_value=weight_value,
                    weight_unit=weight_unit,
                )
            elif step_type == "rest":
                builder.rest(
                    minutes=minutes,
                    seconds=seconds,
                    lap_button=lap_button,
                    description=description,
                )


def _get_table_description(table_name: str) -> str:
    """Get human-readable description for table."""
    descriptions = {
        "daily_health_metrics": "Daily health summaries including steps, sleep, heart rate, stress, and other key metrics",
        "timeseries": "High-frequency data like heart rate readings throughout the day, stress levels, body battery. IMPORTANT: timestamp column is epoch milliseconds (not seconds) — use datetime(timestamp/1000, 'unixepoch', 'localtime') for date filtering and display",
        "activities": "Individual workouts and physical activities with performance metrics",
        "sync_status": "System table tracking data synchronization status (usually not needed for health analysis)",
        "performance_metrics": "Post-activity performance metrics: training load/status, endurance score (updated after activities, not daily)",
        "health_snapshots": "Health Snapshot recordings — on-demand ~2-minute multi-metric measurements taken on a Garmin watch (HR, respiration, stress, SpO2, HRV). One row per snapshot with timing, device metadata, and calendar_date. Sparse — typically a handful per month.",
        "health_snapshot_summaries": "Per-metric summary stats for each health snapshot. summary_type values: HEART_RATE, RESPIRATION, STRESS, SPO2 (each with min/max/avg) plus RMSSD_HRV, SDRR_HRV (avg only — min/max are NULL). Join to health_snapshots on (user_id, activity_uuid).",
        "health_snapshot_zones": "Per-zone time-in-zone for each health snapshot. zone_number 0..5 with millis_in_zone (time spent in zone) and zone_low_boundary (HR threshold for the lower bound). Join to health_snapshots on (user_id, activity_uuid).",
    }
    return descriptions.get(table_name, "Health data table")


def _get_health_data_guide() -> str:
    """Get comprehensive guide for health data analysis."""
    return """
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
**IMPORTANT**: The `timestamp` column stores epoch milliseconds (not seconds). Use `datetime(timestamp/1000, 'unixepoch', 'localtime')` for human-readable times and `timestamp/1000 BETWEEN unixepoch('2026-01-01', 'localtime') AND unixepoch('2026-01-02', 'localtime')` for date filtering.
**USE CASE**: Detailed intraday analysis

### performance_metrics
**WHAT**: Post-activity computed performance metrics
**CONTAINS**: training load (acute/chronic), training status, endurance score with classification
**NOTE**: Updated after activities, not daily. Use "last known value" pattern:
- Latest values: `SELECT * FROM performance_metrics WHERE user_id = 1 AND metric_date <= date('now') ORDER BY metric_date DESC LIMIT 1`
- Training status trend: `SELECT metric_date, training_status, load_type FROM performance_metrics WHERE training_status IS NOT NULL ORDER BY metric_date`

### health_snapshots / health_snapshot_summaries / health_snapshot_zones
**WHAT**: Health Snapshot recordings — on-demand ~2-minute multi-metric measurements taken on a Garmin watch
**CONTAINS**: HR, respiration, stress, SpO2 (min/max/avg) plus RMSSD/SDRR HRV (avg) plus per-zone time
**JOIN KEY**: All three tables key on `(user_id, activity_uuid)`
**NOTE**: These are sparse events (typically a few per month, when the user manually starts a snapshot on the watch). Sync via `sync_health_data` with `metrics='HEALTH_SNAPSHOT'`.
**COMMON QUERIES**:
- Recent snapshots: `SELECT calendar_date, start_timestamp_local FROM health_snapshots WHERE user_id = 1 ORDER BY calendar_date DESC LIMIT 10`
- HRV trend across snapshots: `SELECT s.calendar_date, h.avg_value FROM health_snapshots s JOIN health_snapshot_summaries h USING (user_id, activity_uuid) WHERE h.summary_type = 'RMSSD_HRV' AND s.user_id = 1 ORDER BY s.calendar_date`
- All metrics for one snapshot: `SELECT summary_type, min_value, max_value, avg_value FROM health_snapshot_summaries WHERE user_id = 1 AND activity_uuid = ?`
- Snapshot HR zone time: `SELECT zone_number, millis_in_zone/1000.0 as seconds_in_zone, zone_low_boundary FROM health_snapshot_zones WHERE user_id = 1 AND activity_uuid = ? ORDER BY zone_number`

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
        """.strip()


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
