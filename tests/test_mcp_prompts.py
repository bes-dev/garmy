"""
Comprehensive tests for MCP prompt templates module.

Tests all prompt template functionality to achieve 100% coverage.
"""

from unittest.mock import Mock

import pytest

from garmy.mcp.prompts.templates import PromptTemplates


class TestPromptTemplates:
    """Test suite for PromptTemplates class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_server = Mock()
        self.prompt_templates = PromptTemplates(self.mock_server)

    def test_init(self):
        """Test PromptTemplates initialization."""
        server = Mock()
        templates = PromptTemplates(server)
        assert templates.server is server

    def test_register_prompts(self):
        """Test prompt registration with MCP server."""
        mock_mcp = Mock()
        prompt_functions = {}

        def mock_prompt(func=None):
            def decorator(f):
                prompt_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.prompt = mock_prompt

        self.prompt_templates.register_prompts(mock_mcp)

        # Verify that prompts were registered
        expected_prompts = [
            "health_data_analysis",
            "fitness_goal_planning",
            "sleep_optimization",
            "activity_summary",
        ]

        for prompt_name in expected_prompts:
            assert prompt_name in prompt_functions

    @pytest.mark.asyncio
    async def test_health_data_analysis_prompt(self):
        """Test health data analysis prompt template."""
        mock_mcp = Mock()
        prompt_functions = {}

        def mock_prompt(func=None):
            def decorator(f):
                prompt_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.prompt = mock_prompt

        self.prompt_templates.register_prompts(mock_mcp)

        result = await prompt_functions["health_data_analysis"](
            "sleep", "7", "2023-12-01"
        )

        assert isinstance(result, str)
        assert "analyze" in result.lower()
        assert "sleep" in result.lower()
        assert "7" in result
        assert "2023-12-01" in result
        assert "patterns" in result.lower() or "trends" in result.lower()

    @pytest.mark.asyncio
    async def test_health_data_analysis_prompt_default_params(self):
        """Test health data analysis prompt with default parameters."""
        mock_mcp = Mock()
        prompt_functions = {}

        def mock_prompt(func=None):
            def decorator(f):
                prompt_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.prompt = mock_prompt

        self.prompt_templates.register_prompts(mock_mcp)

        result = await prompt_functions["health_data_analysis"]()

        assert isinstance(result, str)
        assert "analyze" in result.lower()
        # Should have default values
        assert "health" in result.lower()

    @pytest.mark.asyncio
    async def test_fitness_goal_planning_prompt(self):
        """Test fitness goal planning prompt template."""
        mock_mcp = Mock()
        prompt_functions = {}

        def mock_prompt(func=None):
            def decorator(f):
                prompt_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.prompt = mock_prompt

        self.prompt_templates.register_prompts(mock_mcp)

        result = await prompt_functions["fitness_goal_planning"](
            "weight loss", "10000 steps daily"
        )

        assert isinstance(result, str)
        assert "goal" in result.lower()
        assert "weight loss" in result.lower()
        assert "10000 steps daily" in result.lower()
        assert "plan" in result.lower() or "strategy" in result.lower()

    @pytest.mark.asyncio
    async def test_fitness_goal_planning_prompt_default_params(self):
        """Test fitness goal planning prompt with default parameters."""
        mock_mcp = Mock()
        prompt_functions = {}

        def mock_prompt(func=None):
            def decorator(f):
                prompt_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.prompt = mock_prompt

        self.prompt_templates.register_prompts(mock_mcp)

        result = await prompt_functions["fitness_goal_planning"]()

        assert isinstance(result, str)
        assert "fitness" in result.lower()
        assert "goal" in result.lower()

    @pytest.mark.asyncio
    async def test_sleep_optimization_prompt(self):
        """Test sleep optimization prompt template."""
        mock_mcp = Mock()
        prompt_functions = {}

        def mock_prompt(func=None):
            def decorator(f):
                prompt_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.prompt = mock_prompt

        self.prompt_templates.register_prompts(mock_mcp)

        result = await prompt_functions["sleep_optimization"](
            "6.5 hours", "frequent wakings"
        )

        assert isinstance(result, str)
        assert "sleep" in result.lower()
        assert "6.5 hours" in result.lower()
        assert "frequent wakings" in result.lower()
        assert "optimize" in result.lower() or "improve" in result.lower()

    @pytest.mark.asyncio
    async def test_sleep_optimization_prompt_default_params(self):
        """Test sleep optimization prompt with default parameters."""
        mock_mcp = Mock()
        prompt_functions = {}

        def mock_prompt(func=None):
            def decorator(f):
                prompt_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.prompt = mock_prompt

        self.prompt_templates.register_prompts(mock_mcp)

        result = await prompt_functions["sleep_optimization"]()

        assert isinstance(result, str)
        assert "sleep" in result.lower()
        assert "optimize" in result.lower() or "improve" in result.lower()

    @pytest.mark.asyncio
    async def test_activity_summary_prompt(self):
        """Test activity summary prompt template."""
        mock_mcp = Mock()
        prompt_functions = {}

        def mock_prompt(func=None):
            def decorator(f):
                prompt_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.prompt = mock_prompt

        self.prompt_templates.register_prompts(mock_mcp)

        result = await prompt_functions["activity_summary"]("2023-12-01", "2023-12-07")

        assert isinstance(result, str)
        assert "activity" in result.lower() or "activities" in result.lower()
        assert "summary" in result.lower()
        assert "2023-12-01" in result
        assert "2023-12-07" in result

    @pytest.mark.asyncio
    async def test_activity_summary_prompt_default_params(self):
        """Test activity summary prompt with default parameters."""
        mock_mcp = Mock()
        prompt_functions = {}

        def mock_prompt(func=None):
            def decorator(f):
                prompt_functions[f.__name__] = f
                return f

            return decorator(func) if func else decorator

        mock_mcp.prompt = mock_prompt

        self.prompt_templates.register_prompts(mock_mcp)

        result = await prompt_functions["activity_summary"]()

        assert isinstance(result, str)
        assert "activity" in result.lower() or "activities" in result.lower()
        assert "summary" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__])
