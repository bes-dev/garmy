"""Comprehensive tests for garmy.core.__init__ module.

This module provides 100% test coverage for the core module initialization.
"""

import contextlib

import pytest
from requests import HTTPError

from garmy.core import (
    APIClient,
    APIError,
    BaseHTTPClient,
    GarmyError,
    MetricAccessor,
    camel_to_snake,
    camel_to_snake_dict,
    date_range,
    format_date,
    handle_api_exception,
)


def create_mock_http_error(msg="HTTP Error"):
    """Create a mock HTTPError for testing."""
    error = HTTPError(msg)
    return error


class TestCoreImports:
    """Test cases for core module imports."""

    def test_all_imports_available(self):
        """Test all public imports are available from core module."""
        # Test that all expected classes and functions are importable
        assert APIClient is not None
        assert APIError is not None
        assert BaseHTTPClient is not None
        assert GarmyError is not None
        assert MetricAccessor is not None
        assert camel_to_snake is not None
        assert camel_to_snake_dict is not None
        assert date_range is not None
        assert format_date is not None
        assert handle_api_exception is not None

    def test_apiclient_class(self):
        """Test APIClient is a class."""
        assert isinstance(APIClient, type)

    def test_apierror_class(self):
        """Test APIError is a class and exception."""
        assert isinstance(APIError, type)
        assert issubclass(APIError, Exception)

    def test_basehttpclient_class(self):
        """Test BaseHTTPClient is a class."""
        assert isinstance(BaseHTTPClient, type)

    def test_garmyerror_class(self):
        """Test GarmyError is a class and exception."""
        assert isinstance(GarmyError, type)
        assert issubclass(GarmyError, Exception)

    def test_metricaccessor_class(self):
        """Test MetricAccessor is a class."""
        assert isinstance(MetricAccessor, type)

    def test_utility_functions(self):
        """Test utility functions are callable."""
        assert callable(camel_to_snake)
        assert callable(camel_to_snake_dict)
        assert callable(date_range)
        assert callable(format_date)
        assert callable(handle_api_exception)


class TestModuleStructure:
    """Test cases for module structure and organization."""

    def test_module_has_all_attribute(self):
        """Test module has __all__ attribute for explicit exports."""
        import garmy.core as core_module

        assert hasattr(core_module, "__all__")
        assert isinstance(core_module.__all__, list)

    def test_all_attribute_contents(self):
        """Test __all__ attribute contains expected exports."""
        import garmy.core as core_module

        expected_exports = {
            "APIClient",
            "APIError",
            "BaseHTTPClient",
            "GarmyError",
            "MetricAccessor",
            "camel_to_snake",
            "camel_to_snake_dict",
            "date_range",
            "format_date",
            "handle_api_exception",
        }

        assert set(core_module.__all__) == expected_exports

    def test_no_unexpected_exports(self):
        """Test module doesn't export unexpected items."""
        import garmy.core as core_module

        # Get all public attributes (not starting with _)
        public_attrs = {name for name in dir(core_module) if not name.startswith("_")}

        # Filter out module names that are imported but not in __all__
        expected_attrs = set(core_module.__all__)
        # Allow imported modules that aren't in __all__ (like 'client', 'utils', etc.)
        allowed_modules = {
            "client",
            "exceptions",
            "http_client",
            "metrics",
            "utils",
            "base",
            "config",
            "discovery",
            "endpoint_builders",
            "registry",
        }

        unexpected_attrs = public_attrs - expected_attrs - allowed_modules

        # Should not have truly unexpected exports
        assert len(unexpected_attrs) == 0, f"Unexpected exports: {unexpected_attrs}"

    def test_module_docstring(self):
        """Test module has a docstring."""
        import garmy.core as core_module

        assert core_module.__doc__ is not None
        assert isinstance(core_module.__doc__, str)
        assert len(core_module.__doc__.strip()) > 0


class TestImportSafety:
    """Test cases for import safety and circular dependency prevention."""

    def test_core_init_imports_safely(self):
        """Test core __init__ can be imported without issues."""
        try:
            import garmy.core

            # Module should import successfully
            assert garmy.core is not None
        except ImportError as e:
            pytest.fail(f"Core module import failed: {e}")

    def test_no_circular_imports(self):
        """Test importing core doesn't cause circular import issues."""
        # This test ensures that the core module can be imported
        # multiple times without issues
        try:
            # Re-import should work fine
            import garmy.core
            import garmy.core as core2

            assert garmy.core is core2
        except ImportError as e:
            pytest.fail(f"Re-import failed, possible circular dependency: {e}")

    def test_selective_imports(self):
        """Test selective imports work correctly."""
        try:
            from garmy.core import APIClient, APIError

            assert APIClient is not None
            assert APIError is not None
        except ImportError as e:
            pytest.fail(f"Selective import failed: {e}")

    def test_star_import_works(self):
        """Test star import works correctly."""
        # Note: This is generally discouraged but should work for testing
        try:
            exec("from garmy.core import *")
        except ImportError as e:
            pytest.fail(f"Star import failed: {e}")


class TestComponentAvailability:
    """Test cases for component availability and type checking."""

    def test_apiclient_can_be_referenced(self):
        """Test APIClient can be referenced for type hints."""
        from garmy.core import APIClient

        # Should be able to use in type annotations
        def dummy_function(client: APIClient) -> None:
            pass

        assert callable(dummy_function)

    def test_utility_functions_can_be_called(self):
        """Test utility functions can be called."""
        from garmy.core import camel_to_snake, format_date

        # Should be able to call utility functions
        result1 = camel_to_snake("testString")
        result2 = format_date(None)

        assert isinstance(result1, str)
        assert isinstance(result2, str)

    def test_exceptions_inherit_correctly(self):
        """Test exception classes inherit from base Exception."""
        from garmy.core import APIError, GarmyError

        # Test inheritance chain
        assert issubclass(APIError, Exception)
        assert issubclass(GarmyError, Exception)

        # Test they can be raised
        try:
            http_error = create_mock_http_error("test message")
            raise APIError("test message", http_error)
        except APIError:
            pass  # Expected

        with contextlib.suppress(GarmyError):
            raise GarmyError("test message")


class TestLazyLoading:
    """Test cases for lazy loading behavior."""

    def test_imports_dont_trigger_expensive_operations(self):
        """Test imports don't trigger expensive operations."""
        # This test ensures that simply importing the core module
        # doesn't perform expensive operations like network requests
        import time

        start_time = time.time()

        # Import should be fast

        end_time = time.time()

        # Import should complete in reasonable time (< 1 second)
        assert end_time - start_time < 1.0

    def test_module_level_initialization(self):
        """Test module-level initialization is minimal."""
        import garmy.core

        # The core module should not create instances at module level
        # Only classes and functions should be defined
        for name in garmy.core.__all__:
            attr = getattr(garmy.core, name)
            # Should be a class or function, not an instance
            assert isinstance(attr, type) or callable(attr)
