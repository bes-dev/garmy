"""Metric access tools for Garmy MCP server.

Provides tools for accessing and querying Garmin health metrics.
"""

import csv
import io
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any, List, Optional

from fastmcp import Context

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from ..server import GarmyMCPServer

logger = logging.getLogger(__name__)


@dataclass
class DatedMetricData:
    """Wrapper for metric data with associated date."""

    date: date
    data: Any

    def __str__(self) -> str:
        """Format dated metric data for display."""
        if self.data is None:
            return f"**{self.date}**: No data"

        # Special formatting for activities
        if isinstance(self.data, dict) and "activities" in self.data:
            return self._format_activities_data()

        # Standard formatting for other metrics
        data_str = str(self.data)
        return f"**{self.date}**:\n{data_str}"

    def _format_activities_data(self) -> str:
        """Format activities data for display."""
        activities = self.data["activities"]
        count = self.data["count"]

        if count == 0:
            return f"**{self.date}**: No activities"

        result = f"**{self.date}**: {count} activit{'y' if count == 1 else 'ies'}\n"

        for i, activity in enumerate(activities, 1):
            # Get activity details
            name = activity.activity_name or "Unnamed Activity"
            activity_type = getattr(activity, "activity_type_name", "Unknown")
            duration_min = getattr(activity, "duration_minutes", 0)

            result += f"  {i}. {name} ({activity_type})"
            if duration_min:
                result += f" - {duration_min:.0f} min"
            if hasattr(activity, "average_hr") and activity.average_hr:
                result += f" - {activity.average_hr:.0f} bpm avg"
            result += "\n"

        return result.rstrip()


class MetricTools:
    """Metric access tools for MCP server."""

    def __init__(self, server: "GarmyMCPServer"):
        """Initialize metric tools.

        Args:
            server: The parent MCP server instance.
        """
        self.server = server

    def _export_to_csv(self, data_list: List[Any], metric_name: str) -> str:
        """Export data list to CSV format.

        Args:
            data_list: List of metric data objects.
            metric_name: Name of the metric for context.

        Returns:
            CSV formatted string.
        """
        if not data_list:
            return "No data to export"

        output = io.StringIO()

        # Get first object to determine fields
        first_obj = data_list[0]

        if hasattr(first_obj, "__dict__"):
            # Use object attributes as CSV columns
            fieldnames = []
            for key in first_obj.__dict__:
                if not key.startswith("_"):
                    fieldnames.append(key)

            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            for obj in data_list:
                row = {}
                for field in fieldnames:
                    value = getattr(obj, field, None)
                    # Convert complex objects to string representation
                    if isinstance(value, (list, dict)):
                        row[field] = json.dumps(value)
                    elif value is None:
                        row[field] = ""
                    else:
                        row[field] = str(value)
                writer.writerow(row)

        else:
            # Fallback for simple objects
            writer = csv.writer(output)
            writer.writerow([metric_name.replace("_", " ").title()])
            for obj in data_list:
                writer.writerow([str(obj)])

        return output.getvalue()

    def _export_dated_to_csv(
        self, dated_data_list: List[DatedMetricData], metric_name: str
    ) -> str:
        """Export dated data list to CSV format with date column.

        Args:
            dated_data_list: List of DatedMetricData objects.
            metric_name: Name of the metric for context.

        Returns:
            CSV formatted string with date column.
        """
        if not dated_data_list:
            return "No data to export"

        output = io.StringIO()

        # Special handling for activities
        if metric_name == "activities":
            return self._export_activities_to_csv(dated_data_list)

        # Filter out entries with no data
        valid_data = [d for d in dated_data_list if d.data is not None]

        if not valid_data:
            writer = csv.writer(output)
            writer.writerow(["date", metric_name.replace("_", " ").title()])
            writer.writerow(["No data available", ""])
            return output.getvalue()

        # Get first valid object to determine fields
        first_obj = valid_data[0].data

        if hasattr(first_obj, "__dict__"):
            # Use object attributes as CSV columns, with date as first column
            fieldnames = ["date"]
            for key in first_obj.__dict__:
                if not key.startswith("_"):
                    fieldnames.append(key)

            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            for dated_data in reversed(dated_data_list):  # Chronological order
                if dated_data.data is None:
                    # Write row with date but empty data
                    row = {"date": str(dated_data.date)}
                    for field in fieldnames[1:]:
                        row[field] = ""
                    writer.writerow(row)
                else:
                    row = {"date": str(dated_data.date)}
                    for field in fieldnames[1:]:
                        value = getattr(dated_data.data, field, None)
                        # Convert complex objects to string representation
                        if isinstance(value, (list, dict)):
                            row[field] = json.dumps(value)
                        elif value is None:
                            row[field] = ""
                        else:
                            row[field] = str(value)
                    writer.writerow(row)
        else:
            # Fallback for simple objects
            writer = csv.writer(output)
            writer.writerow(["date", metric_name.replace("_", " ").title()])
            for dated_data in reversed(dated_data_list):  # Chronological order
                if dated_data.data is None:
                    writer.writerow([str(dated_data.date), "No data"])
                else:
                    writer.writerow([str(dated_data.date), str(dated_data.data)])

        return output.getvalue()

    def _export_activities_to_csv(self, dated_data_list: List[DatedMetricData]) -> str:
        """Export activities data to CSV format with one row per activity.

        Args:
            dated_data_list: List of DatedMetricData objects containing activities.

        Returns:
            CSV formatted string with one row per activity.
        """
        output = io.StringIO()

        # Collect all activities
        all_activities = []
        for dated_data in dated_data_list:
            if dated_data.data and "activities" in dated_data.data:
                for activity in dated_data.data["activities"]:
                    all_activities.append(activity)

        if not all_activities:
            writer = csv.writer(output)
            writer.writerow(
                ["date", "activity_name", "activity_type", "duration_minutes"]
            )
            writer.writerow(["No activities found", "", "", ""])
            return output.getvalue()

        # Determine fieldnames from first activity
        first_activity = all_activities[0]
        fieldnames = ["date"]  # Always start with date

        if hasattr(first_activity, "__dict__"):
            for key in first_activity.__dict__:
                if not key.startswith("_"):
                    fieldnames.append(key)

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        # Write activities sorted by date (chronological order)
        activities_with_dates = []
        for dated_data in dated_data_list:
            if dated_data.data and "activities" in dated_data.data:
                for activity in dated_data.data["activities"]:
                    activities_with_dates.append((dated_data.date, activity))

        # Sort by date
        activities_with_dates.sort(key=lambda x: x[0])

        for activity_date, activity in activities_with_dates:
            row = {"date": str(activity_date)}

            for field in fieldnames[1:]:
                value = getattr(activity, field, None)
                if isinstance(value, (list, dict)):
                    row[field] = json.dumps(value)
                elif value is None:
                    row[field] = ""
                else:
                    row[field] = str(value)

            writer.writerow(row)

        return output.getvalue()

    def _get_metric_history_with_dates(
        self, metric_name: str, days: int, end_date: Optional[date] = None
    ) -> List[DatedMetricData]:
        """Get metric history with date labels.

        Args:
            metric_name: Name of the metric.
            days: Number of days to fetch.
            end_date: End date (defaults to today).

        Returns:
            List of DatedMetricData objects.
        """
        if end_date is None:
            end_date = date.today()

        # Special handling for activities
        if metric_name == "activities":
            return self._get_activities_history_with_dates(days, end_date)

        # Generate date list (most recent first)
        dates = [end_date - timedelta(days=i) for i in range(days)]

        # Get metric data for each date
        dated_data = []
        for target_date in dates:
            try:
                data = self.server.get_metric_data(metric_name, target_date)
                dated_data.append(DatedMetricData(date=target_date, data=data))
            except Exception as e:
                logger.warning(
                    f"Failed to get {metric_name} data for {target_date}: {e}"
                )
                dated_data.append(DatedMetricData(date=target_date, data=None))

        return dated_data

    def _get_activities_history_with_dates(
        self, days: int, end_date: Optional[date] = None
    ) -> List[DatedMetricData]:
        """Get activities history grouped by dates.

        Args:
            days: Number of days to fetch.
            end_date: End date (defaults to today).

        Returns:
            List of DatedMetricData objects with activities grouped by date.
        """
        if end_date is None:
            end_date = date.today()

        cutoff_date = end_date - timedelta(days=days - 1)

        try:
            # Get activities from API (get more to ensure we capture all in the range)
            activities_accessor = self.server.api_client.metrics.get("activities")
            if not activities_accessor:
                return []

            all_activities = activities_accessor.list(limit=100)  # Get more activities

            # Group activities by date
            activities_by_date = {}
            for activity in all_activities:
                try:
                    # Parse activity date from start_date property
                    activity_date_str = activity.start_date  # YYYY-MM-DD format
                    if activity_date_str:
                        activity_date = datetime.strptime(
                            activity_date_str, "%Y-%m-%d"
                        ).date()

                        # Only include activities in our date range
                        if cutoff_date <= activity_date <= end_date:
                            if activity_date not in activities_by_date:
                                activities_by_date[activity_date] = []
                            activities_by_date[activity_date].append(activity)
                except Exception as e:
                    logger.warning(f"Failed to parse activity date: {e}")
                    continue

            # Create DatedMetricData for each day (most recent first)
            dated_data = []
            for i in range(days):
                target_date = end_date - timedelta(days=i)
                activities_for_date = activities_by_date.get(target_date, [])

                if activities_for_date:
                    # Create a summary of activities for this date
                    activity_summary = {
                        "date": target_date,
                        "count": len(activities_for_date),
                        "activities": activities_for_date,
                    }
                    dated_data.append(
                        DatedMetricData(date=target_date, data=activity_summary)
                    )
                else:
                    dated_data.append(DatedMetricData(date=target_date, data=None))

            return dated_data

        except Exception as e:
            logger.error(f"Failed to get activities history: {e}")
            return [
                DatedMetricData(date=end_date - timedelta(days=i), data=None)
                for i in range(days)
            ]

    def register_tools(self, mcp: "FastMCP"):
        """Register metric tools with the MCP server.

        Args:
            mcp: FastMCP server instance to register tools with.
        """

        @mcp.tool()
        async def list_available_metrics(ctx: Context) -> str:
            """Show all available health metrics."""
            if not self.server.discovered_metrics:
                return "No metrics discovered. Check Garmy installation."

            result = "Available health and fitness metrics:\n\n"

            for i, (name, config) in enumerate(
                self.server.discovered_metrics.items(), 1
            ):
                title = name.replace("_", " ").title()
                description = config.description or "No description available"
                deprecated = " (DEPRECATED)" if config.deprecated else ""

                result += f"{i}. **{title}**{deprecated}\n"
                result += f"   • Key: `{name}`\n"
                result += f"   • {description}\n\n"

            await ctx.info(f"Discovered {len(self.server.discovered_metrics)} metrics")
            return result

        @mcp.tool()
        async def get_metric_data(
            metric_name: str, date_str: Optional[str] = None, ctx: Context = None
        ) -> str:
            """Get metric data for a specific date.

            Args:
                metric_name: Name of the metric (e.g. 'sleep', 'steps', 'heart_rate').
                date_str: Date in YYYY-MM-DD format (defaults to today).
            """
            if not self.server.is_authenticated():
                return "Authentication required. Use garmin_login."

            try:
                target_date = date.today()
                if date_str:
                    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                await ctx.info(f"Getting {metric_name} data for {target_date}")

                # Get data through API
                data = self.server.get_metric_data(metric_name, target_date)

                if not data:
                    return f"No {metric_name} data for {target_date}"

                # Format result
                result = f"**{metric_name.replace('_', ' ').title()}** for {target_date}:\n\n"
                result += self.server.format_metric_data(data, metric_name)

                await ctx.info(f"Successfully retrieved {metric_name} data")
                return result

            except ValueError as e:
                if "Unknown metric" in str(e):
                    available = list(self.server.api_client.metrics.keys())
                    return f"Unknown metric '{metric_name}'. Available: {', '.join(available)}"
                else:
                    return f"Error: {e!s}"
            except Exception as e:
                await ctx.error(f"Error getting data: {e!s}")
                return f"Error: {e!s}"

        @mcp.tool()
        async def get_metric_history(
            metric_name: str,
            days: int = 7,
            end_date: Optional[str] = None,
            ctx: Context = None,
        ) -> str:
            """Get historical metric data for multiple days with date labels.

            Args:
                metric_name: Name of the metric.
                days: Number of days (default 7).
                end_date: End date in YYYY-MM-DD format (defaults to today).
            """
            if not self.server.is_authenticated():
                return "Authentication required. Use garmin_login."

            try:
                target_end = date.today()
                if end_date:
                    target_end = datetime.strptime(end_date, "%Y-%m-%d").date()

                await ctx.info(
                    f"Getting {metric_name} history for {days} days until {target_end}"
                )

                # Get historical data with dates
                dated_history = self._get_metric_history_with_dates(
                    metric_name, days, target_end
                )

                if not dated_history or all(d.data is None for d in dated_history):
                    return f"No historical {metric_name} data"

                result = f"**{metric_name.replace('_', ' ').title()} History** ({days} days until {target_end}):\n\n"

                # Show records with dates (most recent first)
                valid_records = [d for d in dated_history if d.data is not None]
                result += f"Found records: {len(valid_records)} out of {len(dated_history)} days\n\n"

                # Show up to 10 recent records with dates
                records_to_show = dated_history[:10]
                for dated_data in records_to_show:
                    if dated_data.data:
                        result += str(dated_data) + "\n\n"
                    else:
                        result += f"**{dated_data.date}**: No data\n\n"

                if len(dated_history) > 10:
                    result += f"... and {len(dated_history) - 10} more days\n"

                await ctx.info(
                    f"Successfully retrieved {metric_name} history: {len(valid_records)} valid records"
                )
                return result

            except ValueError as e:
                return f"Error: {e!s}"
            except Exception as e:
                await ctx.error(f"Error getting history: {e!s}")
                return f"Error: {e!s}"

        @mcp.tool()
        async def get_metric_range(  # noqa: PLR0911
            metric_name: str,
            start_date: str,
            end_date: Optional[str] = None,
            ctx: Context = None,
        ) -> str:
            """Get metric data for a specific date range with date labels.

            Args:
                metric_name: Name of the metric.
                start_date: Start date in YYYY-MM-DD format.
                end_date: End date in YYYY-MM-DD format (defaults to today).
            """
            if not self.server.is_authenticated():
                return "Authentication required. Use garmin_login."

            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = date.today()
                if end_date:
                    end = datetime.strptime(end_date, "%Y-%m-%d").date()

                if start > end:
                    return "Error: Start date cannot be after end date"

                days = (end - start).days + 1
                if days > self.server.config.max_history_days:
                    return f"Error: Requested range ({days} days) exceeds maximum allowed ({self.server.config.max_history_days} days)"

                await ctx.info(
                    f"Getting {metric_name} data from {start} to {end} ({days} days)"
                )

                # Get range data with dates
                dated_range = self._get_metric_history_with_dates(
                    metric_name, days, end
                )

                if not dated_range or all(d.data is None for d in dated_range):
                    return f"No {metric_name} data for range {start} to {end}"

                result = f"**{metric_name.replace('_', ' ').title()}** from {start} to {end}:\n\n"

                valid_records = [d for d in dated_range if d.data is not None]
                result += f"Found records: {len(valid_records)} out of {days} days\n\n"

                # Show all records for smaller ranges, or summarize for larger ones
                if len(dated_range) <= 15:
                    # Show all records with dates
                    for dated_data in reversed(dated_range):  # Chronological order
                        if dated_data.data:
                            result += str(dated_data) + "\n\n"
                        else:
                            result += f"**{dated_data.date}**: No data\n\n"
                else:
                    # Show first 5 and last 5 with dates
                    result += "**First 5 days:**\n\n"
                    for dated_data in reversed(
                        dated_range[-5:]
                    ):  # First 5 chronologically
                        if dated_data.data:
                            result += str(dated_data) + "\n\n"
                        else:
                            result += f"**{dated_data.date}**: No data\n\n"

                    result += f"... {len(dated_range) - 10} more days ...\n\n"

                    result += "**Last 5 days:**\n\n"
                    for dated_data in dated_range[:5]:  # Last 5 (most recent)
                        if dated_data.data:
                            result += str(dated_data) + "\n\n"
                        else:
                            result += f"**{dated_data.date}**: No data\n\n"

                await ctx.info(
                    f"Successfully retrieved {metric_name} range data: {len(valid_records)} valid records"
                )
                return result

            except ValueError as e:
                if "time data" in str(e):
                    return "Error: Invalid date format. Use YYYY-MM-DD format."
                return f"Error: {e!s}"
            except Exception as e:
                await ctx.error(f"Error getting range data: {e!s}")
                return f"Error: {e!s}"

        @mcp.tool()
        async def export_metric_csv(
            metric_name: str,
            days: int = 30,
            end_date: Optional[str] = None,
            ctx: Context = None,
        ) -> str:
            """Export metric data as CSV for analysis with date columns.

            Args:
                metric_name: Name of the metric.
                days: Number of days to export (default 30).
                end_date: End date in YYYY-MM-DD format (defaults to today).
            """
            if not self.server.is_authenticated():
                return "Authentication required. Use garmin_login."

            try:
                target_end = date.today()
                if end_date:
                    target_end = datetime.strptime(end_date, "%Y-%m-%d").date()

                await ctx.info(
                    f"Exporting {metric_name} data as CSV for {days} days until {target_end}"
                )

                # Get historical data with dates
                dated_history = self._get_metric_history_with_dates(
                    metric_name, days, target_end
                )

                if not dated_history or all(d.data is None for d in dated_history):
                    return f"No {metric_name} data to export"

                # Generate CSV with dates
                csv_content = self._export_dated_to_csv(dated_history, metric_name)

                valid_records = [d for d in dated_history if d.data is not None]
                result = f"**{metric_name.replace('_', ' ').title()} CSV Export** ({len(valid_records)} valid records out of {len(dated_history)} days):\n\n"
                result += "```csv\n"
                result += csv_content
                result += "\n```\n\n"
                result += f"Data exported successfully. Contains {len(valid_records)} valid records from {days} days with date labels."

                await ctx.info(
                    f"Successfully exported {metric_name} data: {len(valid_records)} valid records"
                )
                return result

            except Exception as e:
                await ctx.error(f"Error exporting CSV: {e!s}")
                return f"Error: {e!s}"

        @mcp.tool()
        async def get_metric_schema(metric_name: str, ctx: Context = None) -> str:
            """Get detailed schema information for a metric.

            Args:
                metric_name: Name of the metric to inspect.
            """
            try:
                # Check if metric exists in discovered metrics
                if metric_name not in self.server.discovered_metrics:
                    available = list(self.server.discovered_metrics.keys())
                    return f"Unknown metric '{metric_name}'. Available: {', '.join(available)}"

                config = self.server.discovered_metrics[metric_name]

                result = f"**{metric_name.replace('_', ' ').title()} Schema**:\n\n"
                result += f"• **Class**: {config.metric_class.__name__}\n"
                result += (
                    f"• **Description**: {config.description or 'No description'}\n"
                )
                result += f"• **Version**: {config.version}\n"
                result += f"• **Requires User ID**: {config.requires_user_id}\n"
                result += f"• **Deprecated**: {config.deprecated}\n\n"

                # Get class attributes if possible
                try:
                    if hasattr(config.metric_class, "__dataclass_fields__"):
                        result += "**Available Fields**:\n"
                        for (
                            field_name,
                            field_info,
                        ) in config.metric_class.__dataclass_fields__.items():
                            field_type = (
                                str(field_info.type)
                                .replace("<class '", "")
                                .replace("'>", "")
                            )
                            result += f"• `{field_name}`: {field_type}\n"
                        result += "\n"

                    # Look for properties
                    properties = []
                    for attr_name in dir(config.metric_class):
                        if not attr_name.startswith("_"):
                            attr = getattr(config.metric_class, attr_name, None)
                            if isinstance(attr, property):
                                properties.append(attr_name)

                    if properties:
                        result += "**Computed Properties**:\n"
                        for prop in properties:
                            result += f"• `{prop}`\n"
                        result += "\n"

                except Exception as e:
                    result += f"Schema introspection error: {e!s}\n"

                await ctx.info(f"Retrieved schema for {metric_name}")
                return result

            except Exception as e:
                await ctx.error(f"Error getting schema: {e!s}")
                return f"Error: {e!s}"
