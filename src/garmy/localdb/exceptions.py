"""LocalDB specific exceptions with standardized error handling."""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LocalDBError(Exception):
    """Base exception for LocalDB operations."""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

        super().__init__(self.message)

        # Log the error
        logger.error(f"LocalDB Error [{self.error_code}]: {self.message}", extra={"details": self.details})


class DatabaseError(LocalDBError):
    """Database operation errors."""

    def __init__(self, message: str, operation: str = None, table: str = None, **kwargs):
        details = {"operation": operation, "table": table}
        details.update(kwargs)
        super().__init__(message, "DATABASE_ERROR", details)


class UserNotFoundError(LocalDBError):
    """User not found in database."""

    def __init__(self, user_id: str):
        message = f"User '{user_id}' not found"
        details = {"user_id": user_id}
        super().__init__(message, "USER_NOT_FOUND", details)


class MetricNotFoundError(LocalDBError):
    """Metric data not found."""

    def __init__(self, user_id: str, metric_type: str, data_date: str = None):
        if data_date:
            message = f"Metric '{metric_type}' for user '{user_id}' on '{data_date}' not found"
        else:
            message = f"Metric '{metric_type}' for user '{user_id}' not found"

        details = {"user_id": user_id, "metric_type": metric_type, "data_date": data_date}
        super().__init__(message, "METRIC_NOT_FOUND", details)


class DataConversionError(LocalDBError):
    """Data conversion errors between dataclasses and models."""

    def __init__(self, message: str, dataclass_type: str = None, model_type: str = None, field_name: str = None):
        details = {
            "dataclass_type": dataclass_type,
            "model_type": model_type,
            "field_name": field_name
        }
        super().__init__(message, "DATA_CONVERSION_ERROR", details)


class SyncError(LocalDBError):
    """Synchronization operation errors."""

    def __init__(self, message: str, user_id: str = None, metric_type: str = None, date_range: str = None):
        details = {
            "user_id": user_id,
            "metric_type": metric_type,
            "date_range": date_range
        }
        super().__init__(message, "SYNC_ERROR", details)


class AuthenticationError(LocalDBError):
    """Authentication related errors."""

    def __init__(self, message: str, user_id: str = None):
        details = {"user_id": user_id}
        super().__init__(message, "AUTHENTICATION_ERROR", details)


class ConfigurationError(LocalDBError):
    """Configuration related errors."""

    def __init__(self, message: str, config_key: str = None, config_file: str = None):
        details = {"config_key": config_key, "config_file": config_file}
        super().__init__(message, "CONFIGURATION_ERROR", details)


class ValidationError(LocalDBError):
    """Data validation errors."""

    def __init__(self, message: str, field_name: str = None, field_value: Any = None, expected_type: str = None):
        details = {
            "field_name": field_name,
            "field_value": str(field_value) if field_value is not None else None,
            "expected_type": expected_type
        }
        super().__init__(message, "VALIDATION_ERROR", details)


class ResourceError(LocalDBError):
    """Resource management errors (memory, file handles, etc)."""

    def __init__(self, message: str, resource_type: str = None, resource_path: str = None):
        details = {"resource_type": resource_type, "resource_path": resource_path}
        super().__init__(message, "RESOURCE_ERROR", details)


def handle_safe_operation(operation_name: str, logger: logging.Logger = None):
    """Decorator for standardized error handling in LocalDB operations."""
    if logger is None:
        logger = logging.getLogger(__name__)

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except LocalDBError:
                # Re-raise LocalDB errors as-is (already logged)
                raise
            except Exception as e:
                # Convert other exceptions to LocalDBError
                message = f"Unexpected error in {operation_name}: {e!s}"
                logger.exception(message)
                raise LocalDBError(message, "UNEXPECTED_ERROR", {"operation": operation_name, "original_error": str(e)})

        return wrapper
    return decorator


def safe_execute(operation_name: str, func, *args, **kwargs):
    """Execute function with standardized error handling."""
    try:
        return func(*args, **kwargs)
    except LocalDBError:
        # Re-raise LocalDB errors as-is
        raise
    except Exception as e:
        # Convert other exceptions to LocalDBError
        message = f"Error in {operation_name}: {e!s}"
        logger.exception(message)
        raise LocalDBError(message, "OPERATION_ERROR", {
            "operation": operation_name,
            "original_error": str(e),
            "args": str(args),
            "kwargs": str(kwargs)
        })
