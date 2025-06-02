"""
Base classes and protocols for the metric system.

This module provides the foundational components for the type-safe, auto-discovery
metric architecture. It defines immutable configurations and essential protocols.
"""

from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Optional,
    Protocol,
    Type,
    TypeVar,
    Union,
    runtime_checkable,
)

if TYPE_CHECKING:
    from datetime import date

from .exceptions import ValidationError

T = TypeVar("T")


@dataclass(frozen=True)
class MetricConfig(Generic[T]):
    """
    Immutable configuration for a metric with type safety.

    This configuration class defines all aspects of a metric: endpoint, data class,
    parsing logic, and metadata. The frozen=True ensures immutability.

    Args:
        endpoint: Static API endpoint pattern (may include {date} placeholder)
        metric_class: The dataclass that represents the metric data structure
        parser: Optional custom parsing function for complex data structures
        endpoint_builder: Optional function for dynamic endpoint construction
        requires_user_id: Whether this metric requires user ID in the endpoint
        description: Human-readable description of the metric
        version: Version of the metric implementation
        deprecated: Whether this metric is deprecated
    """

    # Core configuration
    endpoint: str
    metric_class: Type[T]

    # Optional customization
    parser: Optional[Callable[[dict], T]] = None
    endpoint_builder: Optional[Callable[..., str]] = None
    requires_user_id: bool = False

    # Metadata
    description: Optional[str] = None
    version: str = "1.0"
    deprecated: bool = False

    def __post_init__(self) -> None:
        """Validate configuration on creation."""
        # Either endpoint or endpoint_builder must be provided
        if not self.endpoint and not self.endpoint_builder:
            raise ValidationError(
                "Either endpoint or endpoint_builder must be provided"
            )

        # Validate metric class is a dataclass
        if not hasattr(self.metric_class, "__dataclass_fields__"):
            raise ValidationError(
                f"Metric class {self.metric_class} must be a dataclass"
            )


@runtime_checkable
class MetricParser(Protocol):
    """Protocol for metric data parsers."""

    def __call__(self, data: dict) -> Any:
        """Parse raw API response data into a metric object."""
        ...


@runtime_checkable
class EndpointBuilder(Protocol):
    """Protocol for dynamic endpoint builders."""

    def __call__(
        self,
        date_input: Union["date", str, None] = None,
        api_client: Any = None,
        **kwargs: Any,
    ) -> str:
        """Build a dynamic endpoint URL."""
        ...
