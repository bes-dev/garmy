"""Data analysis tools for Garmy MCP server.

Provides tools for analyzing health and fitness trends.
"""

import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING

from fastmcp import Context

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from ..server import GarmyMCPServer

logger = logging.getLogger(__name__)


class AnalysisTools:
    """Data analysis tools for MCP server."""

    def __init__(self, server: "GarmyMCPServer"):
        """Initialize analysis tools.

        Args:
            server: The parent MCP server instance.
        """
        self.server = server

    def register_tools(self, mcp: "FastMCP"):
        """Register analysis tools with the MCP server.

        Args:
            mcp: FastMCP server instance to register tools with.
        """

        @mcp.tool()
        async def analyze_sleep_trends(days: int = 30, ctx: Context = None) -> str:
            """Analyze sleep trends over a specified period.

            Args:
                days: Number of days to analyze (default 30).
            """
            if not self.server.is_authenticated():
                return "Authentication required."

            try:
                await ctx.info(f"Analyzing sleep trends for {days} days")

                sleep_data = self.server.get_metric_history("sleep", days)

                if not sleep_data:
                    return "No sleep data available for analysis"

                # Analyze data
                durations = []
                deep_sleep_percentages = []

                for sleep in sleep_data:
                    if (
                        hasattr(sleep, "sleep_duration_hours")
                        and sleep.sleep_duration_hours
                    ):
                        durations.append(sleep.sleep_duration_hours)
                    if (
                        hasattr(sleep, "deep_sleep_percentage")
                        and sleep.deep_sleep_percentage
                    ):
                        deep_sleep_percentages.append(sleep.deep_sleep_percentage)

                result = f"**Sleep Analysis for {days} days** ({len(sleep_data)} records):\n\n"

                if durations:
                    avg_duration = sum(durations) / len(durations)
                    min_duration = min(durations)
                    max_duration = max(durations)

                    result += "**Sleep Duration:**\n"
                    result += f"• Average: {avg_duration:.1f} hours\n"
                    result += f"• Minimum: {min_duration:.1f} hours\n"
                    result += f"• Maximum: {max_duration:.1f} hours\n\n"

                if deep_sleep_percentages:
                    avg_deep = sum(deep_sleep_percentages) / len(deep_sleep_percentages)
                    result += "**Deep Sleep:**\n"
                    result += f"• Average percentage: {avg_deep:.1f}%\n\n"

                result += "**Recommendations:**\n"
                if durations and avg_duration < 7:
                    result += "• Average sleep duration below recommended (7-9 hours)\n"
                elif durations and avg_duration >= 7:
                    result += "• Good average sleep duration\n"

                await ctx.info("Sleep analysis completed")
                return result

            except Exception as e:
                await ctx.error(f"Analysis error: {e!s}")
                return f"Analysis error: {e!s}"

        @mcp.tool()
        async def compare_metrics(
            metric_name: str,
            period1_days: int = 7,
            period2_days: int = 7,
            ctx: Context = None,
        ) -> str:
            """Compare a metric between two time periods.

            Args:
                metric_name: Name of the metric to compare.
                period1_days: Days for first period (recent).
                period2_days: Days for second period (previous).
            """
            if not self.server.is_authenticated():
                return "Authentication required."

            try:
                await ctx.info(f"Comparing {metric_name} between periods")

                # Get data for both periods
                today = date.today()

                # Period 1 (recent days)
                period1_data = self.server.get_metric_history(
                    metric_name, period1_days, today
                )

                # Period 2 (previous days)
                period2_end = today - timedelta(days=period1_days)
                period2_data = self.server.get_metric_history(
                    metric_name, period2_days, period2_end
                )

                result = f"**{metric_name.replace('_', ' ').title()} Comparison**:\n\n"
                result += f"**Period 1** (last {period1_days} days): {len(period1_data)} records\n"
                result += f"**Period 2** (previous {period2_days} days): {len(period2_data)} records\n\n"

                # Analyze key metrics based on metric type
                if metric_name == "steps":
                    p1_steps = [
                        getattr(d, "total_steps", 0)
                        for d in period1_data
                        if hasattr(d, "total_steps")
                    ]
                    p2_steps = [
                        getattr(d, "total_steps", 0)
                        for d in period2_data
                        if hasattr(d, "total_steps")
                    ]

                    if p1_steps and p2_steps:
                        avg1 = sum(p1_steps) / len(p1_steps)
                        avg2 = sum(p2_steps) / len(p2_steps)
                        change = ((avg1 - avg2) / avg2) * 100 if avg2 > 0 else 0

                        result += "**Average Steps:**\n"
                        result += f"• Period 1: {avg1:,.0f} steps\n"
                        result += f"• Period 2: {avg2:,.0f} steps\n"
                        result += f"• Change: {change:+.1f}%\n"

                elif metric_name == "sleep":
                    p1_duration = [
                        getattr(d, "sleep_duration_hours", 0)
                        for d in period1_data
                        if hasattr(d, "sleep_duration_hours") and d.sleep_duration_hours
                    ]
                    p2_duration = [
                        getattr(d, "sleep_duration_hours", 0)
                        for d in period2_data
                        if hasattr(d, "sleep_duration_hours") and d.sleep_duration_hours
                    ]

                    if p1_duration and p2_duration:
                        avg1 = sum(p1_duration) / len(p1_duration)
                        avg2 = sum(p2_duration) / len(p2_duration)
                        change = avg1 - avg2

                        result += "**Average Sleep Duration:**\n"
                        result += f"• Period 1: {avg1:.1f} hours\n"
                        result += f"• Period 2: {avg2:.1f} hours\n"
                        result += f"• Change: {change:+.1f} hours\n"

                await ctx.info("Comparison completed")
                return result

            except Exception as e:
                await ctx.error(f"Comparison error: {e!s}")
                return f"Comparison error: {e!s}"
