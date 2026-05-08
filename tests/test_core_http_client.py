"""Comprehensive tests for garmy.core.http_client module.

This module provides 100% test coverage for BaseHTTPClient.
"""

from unittest.mock import Mock, patch

import requests
from requests.adapters import HTTPAdapter, Retry

from garmy.core.http_client import BaseHTTPClient


class TestBaseHTTPClient:
    """Test cases for BaseHTTPClient class."""

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_initialization_default(self, mock_get_config):
        """Test BaseHTTPClient initialization with default parameters."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_get_config.return_value = mock_config

        with patch.object(BaseHTTPClient, "_create_session") as mock_create_session:
            mock_session = Mock()
            mock_create_session.return_value = mock_session

            client = BaseHTTPClient()

            assert client.domain == "garmin.com"
            assert client.timeout == 30
            assert client.session == mock_session
            mock_create_session.assert_called_once_with(3, None)

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_initialization_custom(self, mock_get_config):
        """Test BaseHTTPClient initialization with custom parameters."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_get_config.return_value = mock_config

        with patch.object(BaseHTTPClient, "_create_session") as mock_create_session:
            mock_session = Mock()
            mock_create_session.return_value = mock_session

            client = BaseHTTPClient(
                domain="test.com", timeout=60, retries=5, user_agent="custom-agent"
            )

            assert client.domain == "test.com"
            assert client.timeout == 60
            assert client.session == mock_session
            mock_create_session.assert_called_once_with(5, "custom-agent")

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_initialization_none_values(self, mock_get_config):
        """Test BaseHTTPClient initialization with None values uses config defaults."""
        mock_config = Mock()
        mock_config.request_timeout = 45
        mock_config.retries = 4
        mock_get_config.return_value = mock_config

        with patch.object(BaseHTTPClient, "_create_session") as mock_create_session:
            mock_session = Mock()
            mock_create_session.return_value = mock_session

            client = BaseHTTPClient(timeout=None, retries=None)

            assert client.timeout == 45  # From config
            mock_create_session.assert_called_once_with(4, None)  # Config retries

    def test_create_session_basic(self):
        """Test _create_session creates session with basic configuration."""
        with patch("garmy.core.http_client.get_config"):
            client = BaseHTTPClient()

        with patch(
            "garmy.core.http_client.Session"
        ) as mock_session_class, patch.object(
            client, "_get_default_headers", return_value={"Test": "Header"}
        ), patch.object(
            client, "_create_retry_strategy"
        ) as mock_retry:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_retry_strategy = Mock()
            mock_retry.return_value = mock_retry_strategy

            result = client._create_session(3, "test-agent")

            assert result == mock_session
            mock_session.headers.update.assert_called_once_with({"Test": "Header"})
            mock_retry.assert_called_once_with(3)

    def test_create_session_with_adapters(self):
        """Test _create_session mounts HTTP adapters."""
        with patch("garmy.core.http_client.get_config"):
            client = BaseHTTPClient()

        with patch(
            "garmy.core.http_client.Session"
        ) as mock_session_class, patch.object(
            client, "_get_default_headers", return_value={}
        ), patch.object(
            client, "_create_retry_strategy"
        ) as mock_retry, patch(
            "garmy.core.http_client.HTTPAdapter"
        ) as mock_adapter_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_retry_strategy = Mock()
            mock_retry.return_value = mock_retry_strategy
            mock_adapter = Mock()
            mock_adapter_class.return_value = mock_adapter

            client._create_session(3, None)

            # Should create adapter with retry strategy
            mock_adapter_class.assert_called_once_with(max_retries=mock_retry_strategy)

            # Should mount adapter for both http and https
            expected_calls = [
                ("http://", mock_adapter),
                ("https://", mock_adapter),
            ]
            actual_calls = [call[0] for call in mock_session.mount.call_args_list]
            assert actual_calls == expected_calls

    @patch("garmy.core.config.get_user_agent")
    def test_get_default_headers_with_custom_user_agent(self, mock_get_user_agent):
        """Test _get_default_headers with custom user agent."""
        mock_get_user_agent.return_value = "default-agent"

        with patch("garmy.core.http_client.get_config"):
            client = BaseHTTPClient()

        headers = client._get_default_headers("custom-agent")

        expected_headers = {
            "User-Agent": "custom-agent",
            "Accept": "application/json",
        }
        assert headers == expected_headers

    @patch("garmy.core.config.get_user_agent")
    def test_get_default_headers_with_default_user_agent(self, mock_get_user_agent):
        """Test _get_default_headers with default user agent."""
        mock_get_user_agent.return_value = "garmy-default-agent"

        with patch("garmy.core.http_client.get_config"):
            client = BaseHTTPClient()

        headers = client._get_default_headers(None)

        expected_headers = {
            "User-Agent": "garmy-default-agent",
            "Accept": "application/json",
        }
        assert headers == expected_headers
        # Verify that get_user_agent was called with "default"
        mock_get_user_agent.assert_called_with("default")

    @patch("garmy.core.http_client.get_config")
    @patch("garmy.core.http_client.get_retryable_status_codes")
    def test_create_retry_strategy(self, mock_get_retryable_codes, mock_get_config):
        """Test _create_retry_strategy creates correct retry configuration."""
        mock_config = Mock()
        mock_config.backoff_factor = 0.5
        mock_get_config.return_value = mock_config
        mock_get_retryable_codes.return_value = [429, 500, 502, 503, 504]

        client = BaseHTTPClient()

        with patch("garmy.core.http_client.Retry") as mock_retry_class:
            mock_retry_instance = Mock()
            mock_retry_class.return_value = mock_retry_instance

            result = client._create_retry_strategy(5)

            assert result == mock_retry_instance
            mock_retry_class.assert_called_once_with(
                total=5, status_forcelist=[429, 500, 502, 503, 504], backoff_factor=0.5
            )

    def test_get_session(self):
        """Test get_session returns the session."""
        with patch("garmy.core.http_client.get_config"):
            client = BaseHTTPClient()

        mock_session = Mock()
        client.session = mock_session

        result = client.get_session()

        assert result == mock_session

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_real_session_creation(self, mock_get_config):
        """Test BaseHTTPClient creates real session objects."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_config.backoff_factor = 0.3
        mock_get_config.return_value = mock_config

        with patch(
            "garmy.core.http_client.get_retryable_status_codes", return_value=[500, 502]
        ), patch("garmy.core.config.get_user_agent", return_value="test-agent"):
            client = BaseHTTPClient()

        # Should create real session
        assert isinstance(client.session, requests.Session)

        # Should have correct headers
        assert "User-Agent" in client.session.headers
        assert "Accept" in client.session.headers
        assert client.session.headers["Accept"] == "application/json"

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_adapter_configuration(self, mock_get_config):
        """Test BaseHTTPClient configures adapters correctly."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_config.backoff_factor = 0.3
        mock_get_config.return_value = mock_config

        with patch(
            "garmy.core.http_client.get_retryable_status_codes", return_value=[500]
        ), patch("garmy.core.config.get_user_agent", return_value="test-agent"):
            client = BaseHTTPClient()

        # Should have adapters mounted
        assert "http://" in client.session.adapters
        assert "https://" in client.session.adapters

        # Adapters should be HTTPAdapter instances
        http_adapter = client.session.adapters["http://"]
        https_adapter = client.session.adapters["https://"]

        assert isinstance(http_adapter, HTTPAdapter)
        assert isinstance(https_adapter, HTTPAdapter)

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_retry_strategy_configuration(self, mock_get_config):
        """Test BaseHTTPClient configures retry strategy correctly."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 4
        mock_config.backoff_factor = 0.7
        mock_get_config.return_value = mock_config

        with patch(
            "garmy.core.http_client.get_retryable_status_codes", return_value=[429, 500]
        ), patch("garmy.core.config.get_user_agent", return_value="test-agent"):
            client = BaseHTTPClient()

        # Get the adapter to check retry configuration
        adapter = client.session.adapters["https://"]
        retry_strategy = adapter.max_retries

        assert isinstance(retry_strategy, Retry)
        assert retry_strategy.total == 4
        assert retry_strategy.backoff_factor == 0.7
        assert retry_strategy.status_forcelist == [429, 500]


class TestBaseHTTPClientEdgeCases:
    """Test cases for BaseHTTPClient edge cases and error conditions."""

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_zero_retries(self, mock_get_config):
        """Test BaseHTTPClient with zero retries."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_config.backoff_factor = 0.3
        mock_get_config.return_value = mock_config

        with patch(
            "garmy.core.http_client.get_retryable_status_codes", return_value=[500]
        ), patch("garmy.core.config.get_user_agent", return_value="test-agent"):
            client = BaseHTTPClient(retries=0)

        # Should handle zero retries gracefully
        adapter = client.session.adapters["https://"]
        retry_strategy = adapter.max_retries

        assert retry_strategy.total == 0

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_empty_user_agent(self, mock_get_config):
        """Test BaseHTTPClient with empty user agent."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_get_config.return_value = mock_config

        with patch("garmy.core.config.get_user_agent", return_value=""):
            client = BaseHTTPClient(user_agent="")

        # Should handle empty user agent
        assert client.session.headers["User-Agent"] == ""

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_extreme_timeout(self, mock_get_config):
        """Test BaseHTTPClient with extreme timeout values."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_get_config.return_value = mock_config

        # Test very high timeout
        client = BaseHTTPClient(timeout=10000)
        assert client.timeout == 10000

        # Test very low timeout
        client = BaseHTTPClient(timeout=1)
        assert client.timeout == 1

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_extreme_retries(self, mock_get_config):
        """Test BaseHTTPClient with extreme retry values."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_config.backoff_factor = 0.3
        mock_get_config.return_value = mock_config

        with patch(
            "garmy.core.http_client.get_retryable_status_codes", return_value=[500]
        ), patch("garmy.core.config.get_user_agent", return_value="test-agent"):
            # Test high retries
            client = BaseHTTPClient(retries=100)
            adapter = client.session.adapters["https://"]
            assert adapter.max_retries.total == 100

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_special_characters_domain(self, mock_get_config):
        """Test BaseHTTPClient with special characters in domain."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_get_config.return_value = mock_config

        # Should handle domains with special characters
        client = BaseHTTPClient(domain="test-domain.co.uk")
        assert client.domain == "test-domain.co.uk"

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_unicode_user_agent(self, mock_get_config):
        """Test BaseHTTPClient with unicode characters in user agent."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_get_config.return_value = mock_config

        unicode_agent = "garmy-client/1.0 ñáéíóú"
        client = BaseHTTPClient(user_agent=unicode_agent)

        assert client.session.headers["User-Agent"] == unicode_agent


class TestBaseHTTPClientIntegration:
    """Test cases for BaseHTTPClient integration scenarios."""

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_full_configuration_chain(self, mock_get_config):
        """Test BaseHTTPClient full configuration chain."""
        # Setup all mocks
        mock_config = Mock()
        mock_config.request_timeout = 25
        mock_config.retries = 2
        mock_config.backoff_factor = 0.4
        mock_get_config.return_value = mock_config

        with patch(
            "garmy.core.http_client.get_retryable_status_codes",
            return_value=[429, 502, 503],
        ), patch("garmy.core.config.get_user_agent", return_value="integration-agent"):
            client = BaseHTTPClient(
                domain="integration.test.com",
                timeout=35,
                retries=4,
                user_agent="custom-integration-agent",
            )

        # Verify all configuration applied correctly
        assert client.domain == "integration.test.com"
        assert client.timeout == 35
        assert client.session.headers["User-Agent"] == "custom-integration-agent"
        assert client.session.headers["Accept"] == "application/json"

        # Check retry configuration
        adapter = client.session.adapters["https://"]
        retry_strategy = adapter.max_retries
        assert retry_strategy.total == 4
        assert retry_strategy.backoff_factor == 0.4
        assert retry_strategy.status_forcelist == [429, 502, 503]

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_session_reuse(self, mock_get_config):
        """Test BaseHTTPClient session reuse."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_get_config.return_value = mock_config

        client = BaseHTTPClient()

        # Get session multiple times
        session1 = client.get_session()
        session2 = client.get_session()

        # Should return same session instance
        assert session1 is session2
        assert session1 is client.session

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_inheritance_compatibility(self, mock_get_config):
        """Test BaseHTTPClient inheritance compatibility."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_get_config.return_value = mock_config

        class CustomHTTPClient(BaseHTTPClient):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.custom_attribute = "custom_value"

            def custom_method(self):
                return "custom_result"

        client = CustomHTTPClient(domain="custom.com")

        # Should inherit BaseHTTPClient functionality
        assert client.domain == "custom.com"
        assert hasattr(client, "session")
        assert hasattr(client, "timeout")

        # Should have custom functionality
        assert client.custom_attribute == "custom_value"
        assert client.custom_method() == "custom_result"

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_multiple_instances(self, mock_get_config):
        """Test multiple BaseHTTPClient instances."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_get_config.return_value = mock_config

        # Create multiple clients with different configurations
        client1 = BaseHTTPClient(domain="client1.com", timeout=20)
        client2 = BaseHTTPClient(domain="client2.com", timeout=40)

        # Should have independent configurations
        assert client1.domain == "client1.com"
        assert client2.domain == "client2.com"
        assert client1.timeout == 20
        assert client2.timeout == 40

        # Should have independent sessions
        assert client1.session is not client2.session


class TestBaseHTTPClientDependencies:
    """Test cases for BaseHTTPClient dependencies and imports."""

    def test_base_http_client_imports(self):
        """Test BaseHTTPClient imports are available."""
        # Test that all required imports are available
        assert requests.Session is not None
        assert HTTPAdapter is not None
        assert Retry is not None

    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_config_dependency(self, mock_get_config):
        """Test BaseHTTPClient config dependency."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_get_config.return_value = mock_config

        BaseHTTPClient()

        # Should call get_config
        mock_get_config.assert_called()

    @patch("garmy.core.http_client.get_retryable_status_codes")
    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_retryable_codes_dependency(
        self, mock_get_config, mock_get_retryable_codes
    ):
        """Test BaseHTTPClient retryable status codes dependency."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_config.backoff_factor = 0.3
        mock_get_config.return_value = mock_config
        mock_get_retryable_codes.return_value = [500, 502]

        BaseHTTPClient()

        # Should call get_retryable_status_codes during retry strategy creation
        mock_get_retryable_codes.assert_called()

    @patch("garmy.core.config.get_user_agent")
    @patch("garmy.core.http_client.get_config")
    def test_base_http_client_user_agent_dependency(
        self, mock_get_config, mock_get_user_agent
    ):
        """Test BaseHTTPClient user agent dependency."""
        mock_config = Mock()
        mock_config.request_timeout = 30
        mock_config.retries = 3
        mock_get_config.return_value = mock_config
        mock_get_user_agent.return_value = "dependency-agent"

        BaseHTTPClient()

        # Should call get_user_agent for default headers
        mock_get_user_agent.assert_called_with("default")
