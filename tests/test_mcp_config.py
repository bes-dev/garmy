"""
Comprehensive tests for MCP configuration module.

Tests all configuration classes and utilities to achieve 100% coverage.
"""

import os
from unittest.mock import patch

import pytest

from garmy.mcp.config import ConfigManager, MCPConfig, ToolConfig


class TestMCPConfig:
    """Test suite for MCPConfig class."""

    def test_default_initialization(self):
        """Test MCPConfig with default values."""
        config = MCPConfig()

        assert config.server_name == "Garmy Health & Fitness Server"
        assert config.server_version == "1.0.0"
        assert config.enable_auth_tools is True
        assert config.enable_metric_tools is True
        assert config.enable_analysis_tools is True
        assert config.enable_resources is True
        assert config.enable_prompts is True
        assert config.cache_enabled is False
        assert config.cache_size == 100
        assert config.max_history_days == 365
        assert config.default_analysis_period == 30
        assert config.custom_tool_config == {}
        assert config.debug_mode is False

    def test_custom_initialization(self):
        """Test MCPConfig with custom values."""
        custom_config = {"tool1": {"param1": "value1"}}

        config = MCPConfig(
            server_name="Custom Server",
            server_version="2.0.0",
            enable_auth_tools=False,
            cache_enabled=True,
            cache_size=50,
            max_history_days=180,
            default_analysis_period=14,
            custom_tool_config=custom_config,
            debug_mode=True,
        )

        assert config.server_name == "Custom Server"
        assert config.server_version == "2.0.0"
        assert config.enable_auth_tools is False
        assert config.cache_enabled is True
        assert config.cache_size == 50
        assert config.max_history_days == 180
        assert config.default_analysis_period == 14
        assert config.custom_tool_config == custom_config
        assert config.debug_mode is True

    def test_post_init_validation_valid(self):
        """Test successful post-init validation."""
        # Should not raise any exception
        config = MCPConfig(
            max_history_days=30, default_analysis_period=7, cache_size=10
        )
        assert config is not None

    def test_post_init_validation_invalid_max_history_days(self):
        """Test post-init validation with invalid max_history_days."""
        with pytest.raises(ValueError, match="max_history_days must be positive"):
            MCPConfig(max_history_days=0)

        with pytest.raises(ValueError, match="max_history_days must be positive"):
            MCPConfig(max_history_days=-10)

    def test_post_init_validation_invalid_default_analysis_period(self):
        """Test post-init validation with invalid default_analysis_period."""
        with pytest.raises(
            ValueError, match="default_analysis_period must be positive"
        ):
            MCPConfig(default_analysis_period=0)

        with pytest.raises(
            ValueError, match="default_analysis_period must be positive"
        ):
            MCPConfig(default_analysis_period=-5)

    def test_post_init_validation_invalid_cache_size(self):
        """Test post-init validation with invalid cache_size."""
        with pytest.raises(ValueError, match="cache_size must be positive"):
            MCPConfig(cache_size=0)

        with pytest.raises(ValueError, match="cache_size must be positive"):
            MCPConfig(cache_size=-20)

    def test_for_development(self):
        """Test development configuration factory method."""
        config = MCPConfig.for_development()

        assert config.debug_mode is True
        assert config.cache_enabled is True
        assert config.cache_size == 50
        assert config.max_history_days == 90
        # Other values should be defaults
        assert config.server_name == "Garmy Health & Fitness Server"
        assert config.enable_auth_tools is True

    def test_for_production(self):
        """Test production configuration factory method."""
        config = MCPConfig.for_production()

        assert config.debug_mode is False
        assert config.cache_enabled is True
        assert config.cache_size == 200
        assert config.max_history_days == 365
        # Other values should be defaults
        assert config.server_name == "Garmy Health & Fitness Server"
        assert config.enable_auth_tools is True

    def test_minimal(self):
        """Test minimal configuration factory method."""
        config = MCPConfig.minimal()

        assert config.enable_analysis_tools is False
        assert config.enable_resources is False
        assert config.enable_prompts is False
        assert config.cache_enabled is False
        assert config.max_history_days == 30
        # Other values should be defaults
        assert config.server_name == "Garmy Health & Fitness Server"
        assert config.enable_auth_tools is True
        assert config.enable_metric_tools is True


class TestToolConfig:
    """Test suite for ToolConfig class."""

    def test_default_initialization(self):
        """Test ToolConfig with default values."""
        config = ToolConfig()

        assert config.enabled is True
        assert config.rate_limit == 0
        assert config.timeout_seconds == 30
        assert config.custom_params == {}

    def test_custom_initialization(self):
        """Test ToolConfig with custom values."""
        custom_params = {"param1": "value1", "param2": 42}

        config = ToolConfig(
            enabled=False,
            rate_limit=60,
            timeout_seconds=120,
            custom_params=custom_params,
        )

        assert config.enabled is False
        assert config.rate_limit == 60
        assert config.timeout_seconds == 120
        assert config.custom_params == custom_params


class TestConfigManager:
    """Test suite for ConfigManager class."""

    def test_load_from_env_defaults(self):
        """Test loading configuration from environment with no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            config = ConfigManager.load_from_env()

        assert config.debug_mode is False
        assert config.cache_enabled is False
        assert config.cache_size == 100
        assert config.max_history_days == 365
        assert config.default_analysis_period == 30

    def test_load_from_env_debug_true_variations(self):
        """Test loading debug mode with various true values."""
        true_values = ["true", "1", "yes", "on", "TRUE", "True", "YES", "ON"]

        for true_val in true_values:
            with patch.dict(os.environ, {"GARMY_MCP_DEBUG": true_val}):
                config = ConfigManager.load_from_env()
                assert config.debug_mode is True, f"Failed for value: {true_val}"

    def test_load_from_env_debug_false_variations(self):
        """Test loading debug mode with various false values."""
        false_values = ["false", "0", "no", "off", "FALSE", "False", "NO", "OFF"]

        for false_val in false_values:
            with patch.dict(os.environ, {"GARMY_MCP_DEBUG": false_val}):
                config = ConfigManager.load_from_env()
                assert config.debug_mode is False, f"Failed for value: {false_val}"

    def test_load_from_env_debug_invalid_value(self):
        """Test loading debug mode with invalid value falls back to default."""
        with patch.dict(os.environ, {"GARMY_MCP_DEBUG": "maybe"}):
            config = ConfigManager.load_from_env()
            assert config.debug_mode is False  # Should use default

    def test_load_from_env_cache_enabled_true(self):
        """Test loading cache enabled with true value."""
        with patch.dict(os.environ, {"GARMY_MCP_CACHE_ENABLED": "true"}):
            config = ConfigManager.load_from_env()
            assert config.cache_enabled is True

    def test_load_from_env_cache_enabled_false(self):
        """Test loading cache enabled with false value."""
        with patch.dict(os.environ, {"GARMY_MCP_CACHE_ENABLED": "false"}):
            config = ConfigManager.load_from_env()
            assert config.cache_enabled is False

    def test_load_from_env_cache_size_valid(self):
        """Test loading cache size with valid integer."""
        with patch.dict(os.environ, {"GARMY_MCP_CACHE_SIZE": "250"}):
            config = ConfigManager.load_from_env()
            assert config.cache_size == 250

    def test_load_from_env_cache_size_invalid(self):
        """Test loading cache size with invalid value falls back to default."""
        with patch.dict(os.environ, {"GARMY_MCP_CACHE_SIZE": "not_a_number"}):
            config = ConfigManager.load_from_env()
            assert config.cache_size == 100  # Should use default

    def test_load_from_env_max_history_days_valid(self):
        """Test loading max history days with valid integer."""
        with patch.dict(os.environ, {"GARMY_MCP_MAX_HISTORY_DAYS": "180"}):
            config = ConfigManager.load_from_env()
            assert config.max_history_days == 180

    def test_load_from_env_max_history_days_invalid(self):
        """Test loading max history days with invalid value falls back to default."""
        with patch.dict(os.environ, {"GARMY_MCP_MAX_HISTORY_DAYS": "invalid"}):
            config = ConfigManager.load_from_env()
            assert config.max_history_days == 365  # Should use default

    def test_load_from_env_default_analysis_period_valid(self):
        """Test loading default analysis period with valid integer."""
        with patch.dict(os.environ, {"GARMY_MCP_DEFAULT_ANALYSIS_PERIOD": "14"}):
            config = ConfigManager.load_from_env()
            assert config.default_analysis_period == 14

    def test_load_from_env_default_analysis_period_invalid(self):
        """Test loading default analysis period with invalid value falls back to default."""
        with patch.dict(os.environ, {"GARMY_MCP_DEFAULT_ANALYSIS_PERIOD": "not_valid"}):
            config = ConfigManager.load_from_env()
            assert config.default_analysis_period == 30  # Should use default

    def test_load_from_env_all_values_set(self):
        """Test loading configuration with all environment variables set."""
        env_vars = {
            "GARMY_MCP_DEBUG": "true",
            "GARMY_MCP_CACHE_ENABLED": "true",
            "GARMY_MCP_CACHE_SIZE": "150",
            "GARMY_MCP_MAX_HISTORY_DAYS": "200",
            "GARMY_MCP_DEFAULT_ANALYSIS_PERIOD": "21",
        }

        with patch.dict(os.environ, env_vars):
            config = ConfigManager.load_from_env()

        assert config.debug_mode is True
        assert config.cache_enabled is True
        assert config.cache_size == 150
        assert config.max_history_days == 200
        assert config.default_analysis_period == 21

    def test_validate_config_valid(self):
        """Test validating a valid configuration."""
        config = MCPConfig(server_name="Valid Server", server_version="1.0.0")

        # Should not raise any exception
        ConfigManager.validate_config(config)

    def test_validate_config_empty_server_name(self):
        """Test validating configuration with empty server name."""
        config = MCPConfig(server_name="")

        with pytest.raises(ValueError, match="server_name cannot be empty"):
            ConfigManager.validate_config(config)

    def test_validate_config_whitespace_server_name(self):
        """Test validating configuration with whitespace-only server name."""
        config = MCPConfig(server_name="   ")

        with pytest.raises(ValueError, match="server_name cannot be empty"):
            ConfigManager.validate_config(config)

    def test_validate_config_empty_server_version(self):
        """Test validating configuration with empty server version."""
        config = MCPConfig(server_version="")

        with pytest.raises(ValueError, match="server_version cannot be empty"):
            ConfigManager.validate_config(config)

    def test_validate_config_whitespace_server_version(self):
        """Test validating configuration with whitespace-only server version."""
        config = MCPConfig(server_version="   ")

        with pytest.raises(ValueError, match="server_version cannot be empty"):
            ConfigManager.validate_config(config)

    def test_get_garmin_credentials_both_set(self):
        """Test getting Garmin credentials when both are set."""
        with patch.dict(
            os.environ,
            {"GARMIN_EMAIL": "test@example.com", "GARMIN_PASSWORD": "password123"},
        ):
            email, password = ConfigManager.get_garmin_credentials()

        assert email == "test@example.com"
        assert password == "password123"

    def test_get_garmin_credentials_email_only(self):
        """Test getting Garmin credentials when only email is set."""
        with patch.dict(os.environ, {"GARMIN_EMAIL": "test@example.com"}, clear=True):
            email, password = ConfigManager.get_garmin_credentials()

        assert email == "test@example.com"
        assert password is None

    def test_get_garmin_credentials_password_only(self):
        """Test getting Garmin credentials when only password is set."""
        with patch.dict(os.environ, {"GARMIN_PASSWORD": "password123"}, clear=True):
            email, password = ConfigManager.get_garmin_credentials()

        assert email is None
        assert password == "password123"

    def test_get_garmin_credentials_none_set(self):
        """Test getting Garmin credentials when none are set."""
        with patch.dict(os.environ, {}, clear=True):
            email, password = ConfigManager.get_garmin_credentials()

        assert email is None
        assert password is None

    def test_has_garmin_credentials_both_set(self):
        """Test checking for Garmin credentials when both are set."""
        with patch.dict(
            os.environ,
            {"GARMIN_EMAIL": "test@example.com", "GARMIN_PASSWORD": "password123"},
        ):
            result = ConfigManager.has_garmin_credentials()

        assert result is True

    def test_has_garmin_credentials_email_only(self):
        """Test checking for Garmin credentials when only email is set."""
        with patch.dict(os.environ, {"GARMIN_EMAIL": "test@example.com"}, clear=True):
            result = ConfigManager.has_garmin_credentials()

        assert result is False

    def test_has_garmin_credentials_password_only(self):
        """Test checking for Garmin credentials when only password is set."""
        with patch.dict(os.environ, {"GARMIN_PASSWORD": "password123"}, clear=True):
            result = ConfigManager.has_garmin_credentials()

        assert result is False

    def test_has_garmin_credentials_none_set(self):
        """Test checking for Garmin credentials when none are set."""
        with patch.dict(os.environ, {}, clear=True):
            result = ConfigManager.has_garmin_credentials()

        assert result is False

    def test_has_garmin_credentials_empty_values(self):
        """Test checking for Garmin credentials with empty string values."""
        with patch.dict(os.environ, {"GARMIN_EMAIL": "", "GARMIN_PASSWORD": ""}):
            result = ConfigManager.has_garmin_credentials()

        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])
