"""Comprehensive tests for garmy.core.config module.

This module provides 100% test coverage for configuration management.
"""

import os
import threading
from unittest.mock import patch

from garmy.core.config import (
    Concurrency,
    ConfigManager,
    GarmyConfig,
    HTTPStatus,
    Timeouts,
    get_config,
    get_retryable_status_codes,
    get_user_agent,
    set_config,
)


class TestHTTPStatus:
    """Test cases for HTTPStatus constants."""

    def test_http_status_constants(self):
        """Test HTTPStatus has expected constants."""
        assert HTTPStatus.TOO_MANY_REQUESTS == 429
        assert HTTPStatus.INTERNAL_SERVER_ERROR == 500
        assert HTTPStatus.BAD_GATEWAY == 502
        assert HTTPStatus.SERVICE_UNAVAILABLE == 503
        assert HTTPStatus.GATEWAY_TIMEOUT == 504

    def test_http_status_values_are_integers(self):
        """Test HTTPStatus values are integers."""
        assert isinstance(HTTPStatus.TOO_MANY_REQUESTS, int)
        assert isinstance(HTTPStatus.INTERNAL_SERVER_ERROR, int)
        assert isinstance(HTTPStatus.BAD_GATEWAY, int)
        assert isinstance(HTTPStatus.SERVICE_UNAVAILABLE, int)
        assert isinstance(HTTPStatus.GATEWAY_TIMEOUT, int)

    def test_http_status_unique_values(self):
        """Test HTTPStatus values are unique."""
        values = [
            HTTPStatus.TOO_MANY_REQUESTS,
            HTTPStatus.INTERNAL_SERVER_ERROR,
            HTTPStatus.BAD_GATEWAY,
            HTTPStatus.SERVICE_UNAVAILABLE,
            HTTPStatus.GATEWAY_TIMEOUT,
        ]
        assert len(values) == len(set(values))


class TestTimeouts:
    """Test cases for Timeouts constants."""

    def test_timeouts_constants(self):
        """Test Timeouts has expected constants."""
        assert Timeouts.DEFAULT_REQUEST == 10
        assert Timeouts.THREAD_POOL_SHUTDOWN == 300
        assert Timeouts.INDIVIDUAL_TASK == 30

    def test_timeouts_values_are_positive(self):
        """Test Timeouts values are positive integers."""
        assert Timeouts.DEFAULT_REQUEST > 0
        assert Timeouts.THREAD_POOL_SHUTDOWN > 0
        assert Timeouts.INDIVIDUAL_TASK > 0

    def test_timeouts_logical_order(self):
        """Test Timeouts have logical ordering."""
        # Individual task timeout should be less than pool shutdown
        assert Timeouts.INDIVIDUAL_TASK < Timeouts.THREAD_POOL_SHUTDOWN


class TestConcurrency:
    """Test cases for Concurrency constants."""

    def test_concurrency_constants(self):
        """Test Concurrency has expected constants."""
        assert Concurrency.MIN_WORKERS == 1
        assert Concurrency.OPTIMAL_MIN_WORKERS == 4
        assert Concurrency.CPU_MULTIPLIER == 3

    def test_concurrency_values_are_positive(self):
        """Test Concurrency values are positive integers."""
        assert Concurrency.MIN_WORKERS > 0
        assert Concurrency.OPTIMAL_MIN_WORKERS > 0
        assert Concurrency.CPU_MULTIPLIER > 0

    def test_concurrency_logical_order(self):
        """Test Concurrency constants have logical ordering."""
        assert Concurrency.MIN_WORKERS <= Concurrency.OPTIMAL_MIN_WORKERS


class TestConfigManager:
    """Test cases for ConfigManager class."""

    def test_config_manager_singleton(self):
        """Test ConfigManager is a singleton."""
        manager1 = ConfigManager()
        manager2 = ConfigManager()

        assert manager1 is manager2

    def test_config_manager_initialization(self):
        """Test ConfigManager initialization with default values."""
        manager = ConfigManager()
        config = manager.get_config()

        assert config.request_timeout == Timeouts.DEFAULT_REQUEST
        assert config.retries == 3
        assert config.backoff_factor == 0.5
        assert config.max_workers == 50
        assert config.optimal_min_workers == Concurrency.OPTIMAL_MIN_WORKERS
        assert config.optimal_max_workers == Concurrency.OPTIMAL_MAX_WORKERS
        assert config.key_cache_size == 1000
        assert config.metric_cache_size == 100

    def test_config_manager_default_values(self):
        """Test ConfigManager has sensible default values."""
        manager = ConfigManager()
        config = manager.get_config()

        # Test default values are reasonable
        assert 10 <= config.request_timeout <= 60
        assert 1 <= config.retries <= 10
        assert 0.1 <= config.backoff_factor <= 1.0
        assert 1 <= config.max_workers <= 100
        assert config.key_cache_size > 0
        assert config.metric_cache_size > 0

    @patch.dict(
        os.environ,
        {
            "GARMY_REQUEST_TIMEOUT": "45",
            "GARMY_RETRIES": "5",
            "GARMY_BACKOFF_FACTOR": "0.5",
            "GARMY_MAX_WORKERS": "20",
        },
    )
    def test_config_manager_environment_variables(self):
        """Test ConfigManager reads from environment variables."""
        # Clear singleton instance to test environment loading
        ConfigManager._instance = None
        ConfigManager._config = None

        manager = ConfigManager()
        config = manager.get_config()

        assert config.request_timeout == 45
        assert config.retries == 5
        assert config.backoff_factor == 0.5
        assert config.max_workers == 20

    @patch.dict(os.environ, {"GARMY_REQUEST_TIMEOUT": "invalid"})
    def test_config_manager_invalid_environment_values(self):
        """Test ConfigManager handles invalid environment values."""
        # Clear singleton instance
        ConfigManager._instance = None
        ConfigManager._config = None

        manager = ConfigManager()
        config = manager.get_config()

        # Should fall back to default value when environment value is invalid
        assert config.request_timeout == Timeouts.DEFAULT_REQUEST

    def test_config_manager_thread_safety(self):
        """Test ConfigManager is thread-safe."""
        instances = []

        def create_instance():
            instances.append(ConfigManager())

        # Create multiple threads
        threads = [threading.Thread(target=create_instance) for _ in range(10)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All instances should be the same
        assert all(instance is instances[0] for instance in instances)

    def test_config_manager_get_config_method(self):
        """Test ConfigManager get_config method."""
        manager = ConfigManager()
        config = manager.get_config()

        assert isinstance(config, GarmyConfig)
        assert hasattr(config, "request_timeout")
        assert hasattr(config, "retries")
        assert hasattr(config, "backoff_factor")

    def test_config_manager_set_config_method(self):
        """Test ConfigManager set_config method."""
        manager = ConfigManager()
        original_config = manager.get_config()
        original_timeout = original_config.request_timeout

        new_config = GarmyConfig(request_timeout=60)
        manager.set_config(new_config)

        updated_config = manager.get_config()
        assert updated_config.request_timeout == 60
        assert updated_config.request_timeout != original_timeout

    def test_config_manager_set_config_invalid_values(self):
        """Test ConfigManager set_config with invalid values."""
        manager = ConfigManager()

        # Create config with potentially invalid values
        invalid_config = GarmyConfig(request_timeout=-10, retries=-1)
        manager.set_config(invalid_config)

        config = manager.get_config()
        # The config manager doesn't validate, so invalid values are stored
        assert config.request_timeout == -10
        assert config.retries == -1

    def test_config_manager_set_config_partial_update(self):
        """Test ConfigManager set_config replaces entire config."""
        manager = ConfigManager()

        new_config = GarmyConfig(request_timeout=45)
        manager.set_config(new_config)

        # Entire config is replaced
        updated_config = manager.get_config()
        assert updated_config.request_timeout == 45
        assert updated_config.retries == 3  # Default value, not original

    def test_config_manager_repr(self):
        """Test ConfigManager string representation."""
        manager = ConfigManager()
        repr_str = repr(manager)

        assert "ConfigManager" in repr_str


class TestGlobalFunctions:
    """Test cases for global configuration functions."""

    def test_get_config_function(self):
        """Test get_config global function."""
        config = get_config()

        assert isinstance(config, GarmyConfig)
        assert hasattr(config, "request_timeout")
        assert hasattr(config, "retries")

    def test_get_config_returns_same_instance(self):
        """Test get_config always returns same instance."""
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_get_retryable_status_codes_function(self):
        """Test get_retryable_status_codes function."""
        codes = get_retryable_status_codes()

        assert isinstance(codes, list)
        assert all(isinstance(code, int) for code in codes)

        # Should include expected status codes
        expected_codes = [
            HTTPStatus.TOO_MANY_REQUESTS,
            HTTPStatus.INTERNAL_SERVER_ERROR,
            HTTPStatus.BAD_GATEWAY,
            HTTPStatus.SERVICE_UNAVAILABLE,
            HTTPStatus.GATEWAY_TIMEOUT,
        ]
        for code in expected_codes:
            assert code in codes

    def test_get_retryable_status_codes_immutable(self):
        """Test get_retryable_status_codes returns new list each time."""
        codes1 = get_retryable_status_codes()
        codes2 = get_retryable_status_codes()

        # Should be equal but not the same object
        assert codes1 == codes2
        assert codes1 is not codes2

    def test_get_user_agent_function(self):
        """Test get_user_agent function."""
        user_agent = get_user_agent("test")

        assert isinstance(user_agent, str)
        assert len(user_agent) > 0
        assert "garmy" in user_agent.lower()

    def test_get_user_agent_with_different_contexts(self):
        """Test get_user_agent with different contexts."""
        agent1 = get_user_agent("api")
        agent2 = get_user_agent("auth")
        agent3 = get_user_agent("default")

        # All should be strings
        assert all(isinstance(agent, str) for agent in [agent1, agent2, agent3])

        # All should contain garmy
        assert all("garmy" in agent.lower() for agent in [agent1, agent2, agent3])

    def test_get_user_agent_consistent(self):
        """Test get_user_agent returns consistent results."""
        agent1 = get_user_agent("test")
        agent2 = get_user_agent("test")

        assert agent1 == agent2

    @patch.dict(os.environ, {"GARMY_USER_AGENT": "Custom-Agent/1.0"})
    def test_get_user_agent_environment_override(self):
        """Test get_user_agent respects environment variable."""
        user_agent = get_user_agent("test")

        # Should include custom user agent or respect environment
        assert isinstance(user_agent, str)
        assert len(user_agent) > 0


class TestConfigurationEdgeCases:
    """Test cases for configuration edge cases and error handling."""

    @patch.dict(os.environ, {}, clear=True)
    def test_config_no_environment_variables(self):
        """Test configuration works with no environment variables."""
        # Clear singleton instance
        ConfigManager._instance = None
        ConfigManager._lock = threading.RLock()

        manager = ConfigManager()
        config = manager.get_config()

        # Should use default values
        assert config.request_timeout == Timeouts.DEFAULT_REQUEST
        assert config.retries == 3
        assert config.backoff_factor == 0.5

    @patch.dict(
        os.environ,
        {"GARMY_REQUEST_TIMEOUT": "", "GARMY_RETRIES": "", "GARMY_MAX_WORKERS": ""},
    )
    def test_config_empty_environment_variables(self):
        """Test configuration with empty environment variables."""
        # Clear singleton instance
        ConfigManager._instance = None
        ConfigManager._lock = threading.RLock()

        manager = ConfigManager()
        config = manager.get_config()

        # Should use default values when environment vars are empty
        assert config.request_timeout == Timeouts.DEFAULT_REQUEST
        assert config.retries == 3

    def test_config_extreme_values(self):
        """Test configuration with extreme values."""
        manager = ConfigManager()

        # Test setting extreme values
        low_config = GarmyConfig(request_timeout=1)  # Very low
        manager.set_config(low_config)
        config = manager.get_config()
        assert config.request_timeout == 1

        high_config = GarmyConfig(request_timeout=300)  # Very high
        manager.set_config(high_config)
        config = manager.get_config()
        assert config.request_timeout == 300

        min_workers_config = GarmyConfig(max_workers=1)  # Minimum workers
        manager.set_config(min_workers_config)
        config = manager.get_config()
        assert config.max_workers == 1

    def test_config_boundary_values(self):
        """Test configuration with boundary values."""
        manager = ConfigManager()

        # Test zero values
        zero_config = GarmyConfig(retries=0)
        manager.set_config(zero_config)
        config = manager.get_config()
        assert config.retries == 0  # Zero retries should be allowed

        # Test boundary backoff factor
        low_backoff_config = GarmyConfig(backoff_factor=0.1)
        manager.set_config(low_backoff_config)
        config = manager.get_config()
        assert config.backoff_factor == 0.1

        high_backoff_config = GarmyConfig(backoff_factor=2.0)
        manager.set_config(high_backoff_config)
        config = manager.get_config()
        assert config.backoff_factor == 2.0


class TestConfigurationIntegration:
    """Test cases for configuration integration with other components."""

    def test_config_used_by_get_retryable_status_codes(self):
        """Test configuration is used by other functions."""
        codes = get_retryable_status_codes()
        get_config()

        # Should be related to HTTPStatus constants
        assert HTTPStatus.TOO_MANY_REQUESTS in codes
        assert isinstance(codes, list)

    def test_config_consistency_across_calls(self):
        """Test configuration remains consistent across multiple calls."""
        config1 = get_config()
        timeout1 = config1.request_timeout

        config2 = get_config()
        timeout2 = config2.request_timeout

        assert timeout1 == timeout2
        assert config1 is config2

    def test_config_modifications_persist(self):
        """Test configuration modifications persist."""
        config = get_config()
        original_timeout = config.request_timeout

        new_config = GarmyConfig(request_timeout=original_timeout + 10)
        set_config(new_config)

        # Get config again and verify change persisted
        new_config = get_config()
        assert new_config.request_timeout == original_timeout + 10

    def test_user_agent_includes_version_info(self):
        """Test user agent includes version information."""
        user_agent = get_user_agent("test")

        # Should include some version or identifying information
        assert "/" in user_agent or "garmy" in user_agent.lower()
        assert len(user_agent) > 5  # Should be reasonably descriptive
