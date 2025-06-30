"""Configuration management for Garmin LocalDB MCP Server."""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass


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
    
    @classmethod
    def from_db_path(cls, db_path: Path, **kwargs) -> "MCPConfig":
        """Create config with database path and optional overrides."""
        return cls(db_path=db_path, **kwargs)
    
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