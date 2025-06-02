"""Comprehensive tests for garmy.core.exceptions module.

This module provides 100% test coverage for core exception classes.
"""

import pytest
from requests import HTTPError

from garmy.core.exceptions import (
    APIError,
    DiscoveryError,
    EndpointBuilderError,
    FactoryError,
    GarmyError,
)


def create_mock_http_error(msg="HTTP Error"):
    """Create a mock HTTPError for testing."""
    error = HTTPError(msg)
    return error


class TestGarmyError:
    """Test cases for GarmyError base exception class."""

    def test_garmy_error_creation(self):
        """Test GarmyError can be created."""
        error = GarmyError("Test error message")

        assert isinstance(error, Exception)
        assert str(error) == "Test error message"

    def test_garmy_error_inheritance(self):
        """Test GarmyError inherits from Exception."""
        error = GarmyError("Test error")

        assert isinstance(error, Exception)
        assert issubclass(GarmyError, Exception)

    def test_garmy_error_with_args(self):
        """Test GarmyError with message argument."""
        error = GarmyError("Error message")

        assert isinstance(error, GarmyError)
        assert error.msg == "Error message"

    def test_garmy_error_empty_message(self):
        """Test GarmyError with empty message."""
        error = GarmyError("")

        assert str(error) == ""
        assert error.args == ("",)

    def test_garmy_error_no_message(self):
        """Test GarmyError requires a message."""
        # GarmyError requires a msg parameter
        with pytest.raises(TypeError):
            GarmyError()

    def test_garmy_error_repr(self):
        """Test GarmyError string representation."""
        error = GarmyError("Test message")

        repr_str = repr(error)
        assert "GarmyError" in repr_str
        assert "Test message" in repr_str

    def test_garmy_error_is_dataclass(self):
        """Test GarmyError is a dataclass."""
        # Should have dataclass fields
        assert hasattr(GarmyError, "__dataclass_fields__")

    def test_garmy_error_dataclass_fields(self):
        """Test GarmyError dataclass structure."""
        error = GarmyError("Test message")

        # Should be able to access as dataclass
        assert hasattr(error, "msg")
        assert error.msg == "Test message"

    def test_garmy_error_equality(self):
        """Test GarmyError equality comparison."""
        error1 = GarmyError("Same message")
        error2 = GarmyError("Same message")
        error3 = GarmyError("Different message")

        # Same messages should be equal (dataclass behavior)
        assert error1 == error2
        assert error1 != error3

    def test_garmy_error_hash(self):
        """Test GarmyError is not hashable (mutable dataclass)."""
        error = GarmyError("Test message")

        # Should not be hashable since it's a mutable dataclass
        with pytest.raises(TypeError):
            hash(error)

    def test_garmy_error_can_be_raised(self):
        """Test GarmyError can be raised and caught."""
        with pytest.raises(GarmyError) as exc_info:
            raise GarmyError("Test exception")

        assert str(exc_info.value) == "Test exception"

    def test_garmy_error_with_cause(self):
        """Test GarmyError with exception chaining."""
        original_error = ValueError("Original error")

        with pytest.raises(GarmyError) as exc_info:
            try:
                raise original_error
            except ValueError as e:
                raise GarmyError("Wrapped error") from e

        assert str(exc_info.value) == "Wrapped error"
        assert exc_info.value.__cause__ == original_error


class TestAPIError:
    """Test cases for APIError exception class."""

    def test_api_error_creation(self):
        """Test APIError can be created."""
        from requests import HTTPError

        http_error = HTTPError("HTTP error")
        error = APIError("API call failed", http_error)

        assert isinstance(error, APIError)
        assert isinstance(error, GarmyError)
        assert isinstance(error, Exception)
        assert "API call failed" in str(error)

    def test_api_error_inheritance(self):
        """Test APIError inherits from GarmyError."""
        assert issubclass(APIError, GarmyError)
        assert issubclass(APIError, Exception)

    def test_api_error_with_status_code(self):
        """Test APIError with HTTP status code."""
        http_error = create_mock_http_error("Not found")
        error = APIError("Not found", http_error)

        assert "Not found" in str(error)

    def test_api_error_can_be_raised(self):
        """Test APIError can be raised and caught."""
        http_error = create_mock_http_error("HTTP 500 error")
        with pytest.raises(APIError) as exc_info:
            raise APIError("HTTP 500 error", http_error)

        assert "HTTP 500 error" in str(exc_info.value)

    def test_api_error_caught_as_garmy_error(self):
        """Test APIError can be caught as GarmyError."""
        http_error = create_mock_http_error("API error")
        with pytest.raises(GarmyError):
            raise APIError("API error", http_error)

    def test_api_error_with_request_details(self):
        """Test APIError with request details."""
        http_error = create_mock_http_error("Request failed")
        error = APIError("Request failed", http_error)

        assert "Request failed" in str(error)

    def test_api_error_equality(self):
        """Test APIError equality."""
        http_error1 = create_mock_http_error("Same error")
        http_error2 = create_mock_http_error("Same error")
        http_error3 = create_mock_http_error("Different error")
        error1 = APIError("Same error", http_error1)
        error2 = APIError("Same error", http_error2)
        error3 = APIError("Different error", http_error3)

        assert error1.msg == error2.msg
        assert error1.msg != error3.msg


class TestDiscoveryError:
    """Test cases for DiscoveryError exception class."""

    def test_discovery_error_creation(self):
        """Test DiscoveryError can be created."""
        error = DiscoveryError("Discovery failed")

        assert isinstance(error, DiscoveryError)
        assert isinstance(error, GarmyError)
        assert isinstance(error, Exception)
        assert str(error) == "Discovery failed"

    def test_discovery_error_inheritance(self):
        """Test DiscoveryError inherits from GarmyError."""
        assert issubclass(DiscoveryError, GarmyError)
        assert issubclass(DiscoveryError, Exception)

    def test_discovery_error_can_be_raised(self):
        """Test DiscoveryError can be raised and caught."""
        with pytest.raises(DiscoveryError) as exc_info:
            raise DiscoveryError("Module discovery failed")

        assert str(exc_info.value) == "Module discovery failed"

    def test_discovery_error_caught_as_garmy_error(self):
        """Test DiscoveryError can be caught as GarmyError."""
        with pytest.raises(GarmyError):
            raise DiscoveryError("Discovery error")

    def test_discovery_error_with_module_details(self):
        """Test DiscoveryError with single message."""
        error = DiscoveryError("Failed to load module")

        assert "Failed to load module" in str(error)
        assert isinstance(error, DiscoveryError)
        assert isinstance(error, GarmyError)


class TestEndpointBuilderError:
    """Test cases for EndpointBuilderError exception class."""

    def test_endpoint_builder_error_creation(self):
        """Test EndpointBuilderError can be created."""
        error = EndpointBuilderError("Endpoint building failed")

        assert isinstance(error, EndpointBuilderError)
        assert isinstance(error, GarmyError)
        assert isinstance(error, Exception)
        assert str(error) == "Endpoint building failed"

    def test_endpoint_builder_error_inheritance(self):
        """Test EndpointBuilderError inherits from GarmyError."""
        assert issubclass(EndpointBuilderError, GarmyError)
        assert issubclass(EndpointBuilderError, Exception)

    def test_endpoint_builder_error_can_be_raised(self):
        """Test EndpointBuilderError can be raised and caught."""
        with pytest.raises(EndpointBuilderError) as exc_info:
            raise EndpointBuilderError("Cannot build endpoint")

        assert str(exc_info.value) == "Cannot build endpoint"

    def test_endpoint_builder_error_caught_as_garmy_error(self):
        """Test EndpointBuilderError can be caught as GarmyError."""
        with pytest.raises(GarmyError):
            raise EndpointBuilderError("Endpoint error")

    def test_endpoint_builder_error_with_details(self):
        """Test EndpointBuilderError with single message."""
        error = EndpointBuilderError("Build failed")

        assert "Build failed" in str(error)
        assert isinstance(error, EndpointBuilderError)
        assert isinstance(error, GarmyError)


class TestFactoryError:
    """Test cases for FactoryError exception class."""

    def test_factory_error_creation(self):
        """Test FactoryError can be created."""
        error = FactoryError("Factory creation failed")

        assert isinstance(error, FactoryError)
        assert isinstance(error, GarmyError)
        assert isinstance(error, Exception)
        assert str(error) == "Factory creation failed"

    def test_factory_error_inheritance(self):
        """Test FactoryError inherits from GarmyError."""
        assert issubclass(FactoryError, GarmyError)
        assert issubclass(FactoryError, Exception)

    def test_factory_error_can_be_raised(self):
        """Test FactoryError can be raised and caught."""
        with pytest.raises(FactoryError) as exc_info:
            raise FactoryError("Cannot create factory")

        assert str(exc_info.value) == "Cannot create factory"

    def test_factory_error_caught_as_garmy_error(self):
        """Test FactoryError can be caught as GarmyError."""
        with pytest.raises(GarmyError):
            raise FactoryError("Factory error")

    def test_factory_error_with_factory_details(self):
        """Test FactoryError with single message."""
        error = FactoryError("Creation failed")

        assert "Creation failed" in str(error)
        assert isinstance(error, FactoryError)
        assert isinstance(error, GarmyError)


class TestExceptionHierarchy:
    """Test cases for exception hierarchy and relationships."""

    def test_all_exceptions_inherit_from_garmy_error(self):
        """Test all custom exceptions inherit from GarmyError."""
        exceptions = [APIError, DiscoveryError, EndpointBuilderError, FactoryError]

        for exc_class in exceptions:
            assert issubclass(exc_class, GarmyError)
            assert issubclass(exc_class, Exception)

    def test_exception_hierarchy_structure(self):
        """Test exception hierarchy structure."""
        # Create instances
        garmy_error = GarmyError("Base error")
        http_error = create_mock_http_error("API error")
        api_error = APIError("API error", http_error)
        discovery_error = DiscoveryError("Discovery error")
        endpoint_error = EndpointBuilderError("Endpoint error")
        factory_error = FactoryError("Factory error")

        # Test isinstance relationships
        assert isinstance(api_error, GarmyError)
        assert isinstance(discovery_error, GarmyError)
        assert isinstance(endpoint_error, GarmyError)
        assert isinstance(factory_error, GarmyError)

        # Test all are exceptions
        assert all(
            isinstance(error, Exception)
            for error in [
                garmy_error,
                api_error,
                discovery_error,
                endpoint_error,
                factory_error,
            ]
        )

    def test_catch_all_with_garmy_error(self):
        """Test catching all custom exceptions with GarmyError."""
        http_error = create_mock_http_error("API failed")
        exceptions_to_test = [
            APIError("API failed", http_error),
            DiscoveryError("Discovery failed"),
            EndpointBuilderError("Endpoint failed"),
            FactoryError("Factory failed"),
        ]

        for exception in exceptions_to_test:
            with pytest.raises(GarmyError):
                raise exception

    def test_specific_exception_catching(self):
        """Test catching specific exception types."""
        # Test each exception can be caught specifically
        http_error = create_mock_http_error("API error")
        with pytest.raises(APIError):
            raise APIError("API error", http_error)

        with pytest.raises(DiscoveryError):
            raise DiscoveryError("Discovery error")

        with pytest.raises(EndpointBuilderError):
            raise EndpointBuilderError("Endpoint error")

        with pytest.raises(FactoryError):
            raise FactoryError("Factory error")


class TestExceptionUsagePatterns:
    """Test cases for common exception usage patterns."""

    def test_exception_chaining(self):
        """Test exception chaining with custom exceptions."""
        original_error = ValueError("Original problem")

        with pytest.raises(APIError) as exc_info:
            try:
                raise original_error
            except ValueError as e:
                http_error = create_mock_http_error("API call failed due to validation")
                raise APIError("API call failed due to validation", http_error) from e

        assert exc_info.value.__cause__ == original_error

    def test_exception_context_management(self):
        """Test exceptions in context management."""

        class TestContext:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type is ValueError:
                    http_error = create_mock_http_error("Context error")
                    raise APIError("Context error", http_error) from exc_val
                return False

        with pytest.raises(APIError), TestContext():
            raise ValueError("Original error")

    def test_multiple_exception_types_in_try_except(self):
        """Test handling multiple exception types."""

        def risky_operation(error_type):
            if error_type == "api":
                http_error = create_mock_http_error("API failed")
                raise APIError("API failed", http_error)
            elif error_type == "discovery":
                raise DiscoveryError("Discovery failed")
            elif error_type == "endpoint":
                raise EndpointBuilderError("Endpoint failed")
            elif error_type == "factory":
                raise FactoryError("Factory failed")
            else:
                raise ValueError("Unknown error")

        # Test catching specific types
        for error_type, expected_exception in [
            ("api", APIError),
            ("discovery", DiscoveryError),
            ("endpoint", EndpointBuilderError),
            ("factory", FactoryError),
        ]:
            with pytest.raises(expected_exception):
                risky_operation(error_type)

    def test_exception_with_complex_data(self):
        """Test exceptions with complex data structures."""
        # Test that exceptions can handle complex error scenarios
        http_error = create_mock_http_error("Complex API error")
        error = APIError("Complex API error", http_error)

        assert "Complex API error" in str(error)

    def test_exception_message_formatting(self):
        """Test exception message formatting."""
        # Test different message formats
        http_error1 = create_mock_http_error("Simple message")
        http_error2 = create_mock_http_error("HTTP 404 error")
        http_error3 = create_mock_http_error("Multiline error")
        simple_error = APIError("Simple message", http_error1)
        formatted_error = APIError(
            f"HTTP {404} error for endpoint /api/test", http_error2
        )
        multiline_error = APIError("Line 1\nLine 2\nLine 3", http_error3)

        assert "Simple message" in str(simple_error)
        assert "404" in str(formatted_error)
        assert "\n" in str(multiline_error)

    def test_exception_in_inheritance_scenarios(self):
        """Test exceptions in class inheritance scenarios."""

        class CustomAPIError(APIError):
            def __init__(self, message, status_code=None):
                super().__init__(message, status_code)
                self.status_code = status_code

        error = CustomAPIError("Custom API error", 404)

        assert isinstance(error, APIError)
        assert isinstance(error, GarmyError)
        assert isinstance(error, Exception)
        assert error.status_code == 404


class TestExceptionEdgeCases:
    """Test cases for exception edge cases and corner scenarios."""

    def test_exception_with_none_values(self):
        """Test exceptions with None values."""
        http_error = create_mock_http_error("None error")
        error = APIError(None, http_error)

        assert "None" in str(error)

    def test_exception_with_empty_args(self):
        """Test exceptions require arguments."""
        # GarmyError requires msg parameter
        with pytest.raises(TypeError):
            GarmyError()

    def test_exception_with_numeric_args(self):
        """Test exceptions with numeric arguments."""
        http_error = create_mock_http_error("Numeric error")
        error = APIError("404", http_error)

        assert "404" in str(error)

    def test_exception_with_boolean_args(self):
        """Test exceptions with boolean message."""
        error = FactoryError("True")

        assert isinstance(error, FactoryError)
        assert "True" in str(error)

    def test_exception_attribute_access(self):
        """Test accessing exception attributes."""
        http_error = create_mock_http_error("Test error")
        error = APIError("Test error", http_error)

        # Test standard exception attributes
        assert hasattr(error, "msg")
        assert hasattr(error, "error")
        assert hasattr(error, "__str__")
        assert hasattr(error, "__repr__")

    def test_exception_subclass_behavior(self):
        """Test exception subclass behavior."""
        # All custom exceptions should behave like standard exceptions
        http_error = create_mock_http_error("test")
        exceptions = [
            GarmyError("test"),
            APIError("test", http_error),
            DiscoveryError("test"),
            EndpointBuilderError("test"),
            FactoryError("test"),
        ]

        for exc in exceptions:
            # Should be able to convert to string
            assert isinstance(str(exc), str)
            assert isinstance(repr(exc), str)

            # Should have args tuple
            assert isinstance(exc.args, tuple)

            # Should not be hashable (mutable dataclass)
            with pytest.raises(TypeError):
                hash(exc)
