"""Prompt templates for Garmy MCP server.

Provides structured prompt templates for health data analysis.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from ..server import GarmyMCPServer

logger = logging.getLogger(__name__)


class PromptTemplates:
    """Prompt templates for MCP server."""

    def __init__(self, server: "GarmyMCPServer"):
        """Initialize prompt templates.

        Args:
            server: The parent MCP server instance.
        """
        self.server = server

    def register_prompts(self, mcp: "FastMCP"):
        """Register prompts with the MCP server.

        Args:
            mcp: FastMCP server instance to register prompts with.
        """

        @mcp.prompt()
        def analyze_health_data(metric_type: str, time_period: str = "week") -> str:
            """Generate a prompt for analyzing health data.

            Args:
                metric_type: Type of metric (sleep, steps, heart_rate, etc.).
                time_period: Analysis period (day, week, month).
            """
            return f"""
Analyze the {metric_type} data for the past {time_period} and provide:

1. **Key Metrics**: averages, minimums, maximums
2. **Trends**: improvement or decline patterns
3. **Patterns**: regularity, anomalies
4. **Recommendations**: specific advice for health improvement
5. **Goals**: suggested targets for next period

Make the analysis clear and actionable, with specific numbers and recommendations.
"""

        @mcp.prompt()
        def health_summary_request(period_days: int = 7) -> str:
            """Prompt for creating a comprehensive health summary.

            Args:
                period_days: Number of days for the summary.
            """
            return f"""
Create a comprehensive health and fitness summary for the last {period_days} days:

**Include these sections:**

1. **💤 Sleep**: quality, duration, patterns
2. **🚶 Activity**: steps, distance, calories
3. **❤️ Cardio**: resting heart rate, variability, zones
4. **😰 Stress**: levels, recovery, balance
5. **🔋 Energy**: Body Battery, charging/draining trends
6. **🏃 Readiness**: training readiness, contributing factors

**For each section provide:**
- Key metrics and trends
- Comparison with previous period
- Improvement recommendations
- Risk warnings

Make the summary personal and actionable.
"""

        @mcp.prompt()
        def training_analysis_request(metric_focus: str = "training_readiness") -> str:
            """Prompt for training-focused analysis.

            Args:
                metric_focus: Primary metric to focus on.
            """
            return f"""
Analyze training and recovery data with focus on {metric_focus}:

**Training Analysis:**
1. **Readiness Trends**: daily scores and factors
2. **Recovery Patterns**: sleep, HRV, stress impact
3. **Training Load**: acute vs chronic workload
4. **Performance Indicators**: heart rate zones, recovery time

**Recommendations:**
1. **Training Schedule**: when to push vs rest
2. **Recovery Strategies**: sleep, stress management
3. **Performance Optimization**: training intensity guidance
4. **Risk Management**: overtraining prevention

Focus on actionable insights for athletic performance.
"""

        @mcp.prompt()
        def wellness_trend_analysis(metrics: str = "sleep,stress,hrv") -> str:
            """Prompt for wellness trend analysis.

            Args:
                metrics: Comma-separated list of metrics to analyze.
            """
            metric_list = [m.strip() for m in metrics.split(",")]

            return f"""
Analyze wellness trends across multiple metrics: {", ".join(metric_list)}

**Cross-Metric Analysis:**
1. **Correlations**: how metrics influence each other
2. **Patterns**: weekly/monthly cycles
3. **Triggers**: factors affecting wellness
4. **Recovery**: bounce-back patterns

**Holistic Recommendations:**
1. **Lifestyle Adjustments**: daily habits
2. **Stress Management**: techniques and timing
3. **Sleep Optimization**: quality improvement
4. **Overall Wellness**: balanced approach

Provide insights that connect the metrics for comprehensive wellness understanding.
"""
