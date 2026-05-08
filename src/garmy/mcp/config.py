"""Configuration management for Garmin LocalDB MCP Server."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class MCPConfig:
    """Configuration for MCP server behavior and security settings."""

    # Database settings
    db_path: Path

    # Query execution limits
    max_rows: int = 1000
    max_rows_absolute: int = 5000

    # Security settings
    enable_query_logging: bool = False
    strict_validation: bool = True

    # Network/transport settings
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000

    # Sync settings
    enable_sync: bool = False
    profile_path: Optional[Path] = None

    # Workout settings (requires authentication)
    enable_workouts: bool = False

    @classmethod
    def from_db_path(cls, db_path: Path, **kwargs) -> "MCPConfig":
        """Create config with database path and optional overrides."""
        return cls(db_path=db_path, **kwargs)

    @property
    def token_dir(self) -> Optional[str]:
        """Get token directory from profile path if set."""
        if self.profile_path:
            return str(self.profile_path)
        return None

    def validate(self) -> None:
        """Validate configuration settings."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        if not self.db_path.is_file():
            raise ValueError(f"Path is not a file: {self.db_path}")

        if self.max_rows > self.max_rows_absolute:
            raise ValueError(f"max_rows cannot exceed {self.max_rows_absolute}")

        if self.max_rows <= 0:
            raise ValueError("max_rows must be positive")

        # Validate transport settings
        valid_transports = ("stdio", "http", "sse")
        if self.transport not in valid_transports:
            raise ValueError(
                f"Invalid transport: {self.transport}. "
                f"Must be one of: {', '.join(valid_transports)}"
            )

        if self.transport in ("http", "sse"):
            if self.port < 1 or self.port > 65535:
                raise ValueError(f"Port must be between 1 and 65535, got {self.port}")
