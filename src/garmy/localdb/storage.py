"""Local data storage implementation using SQLite."""

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterator, Tuple, Union
import hashlib
import uuid

from .config import LocalDBConfig, UserConfig
from .exceptions import (
    LocalDBError,
    DataIntegrityError,
    UserNotFoundError,
    LockError,
)


class LocalDataStore:
    """Local data storage using SQLite with multi-user support."""
    
    def __init__(self, config: LocalDBConfig) -> None:
        self.config = config
        self._db: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()
        self._users_cache: Dict[str, UserConfig] = {}
        self._transaction_locks: Dict[str, threading.Lock] = {}
    
    def __enter__(self) -> "LocalDataStore":
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
    
    def open(self) -> None:
        """Open the database connection."""
        if self._db is not None:
            return
        
        try:
            # Ensure database directory exists
            self.config.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Open SQLite database
            self._db = sqlite3.connect(
                str(self.config.db_path),
                check_same_thread=False,  # Allow multi-threading
                timeout=self.config.timeout,
            )
            
            # Configure database
            self._db.execute(f"PRAGMA journal_mode={self.config.journal_mode}")
            self._db.execute(f"PRAGMA synchronous={self.config.synchronous_mode}")
            self._db.execute("PRAGMA foreign_keys=ON")  # Enable foreign keys
            self._db.execute(f"PRAGMA temp_store={self.config.temp_store}")
            self._db.execute(f"PRAGMA cache_size={self.config.cache_size}")
            
            # Set page size (only works on empty database)
            page_size = 65536 if self.config.compression else self.config.page_size
            self._db.execute(f"PRAGMA page_size={page_size}")
            
            # Create tables
            self._create_tables()
            self._load_users()
            
        except Exception as e:
            raise LocalDBError(f"Failed to open database: {e}")
    
    def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            self._db.close()
            self._db = None
    
    def _create_tables(self) -> None:
        """Create database tables."""
        if self._db is None:
            raise LocalDBError("Database not open")
        
        # Users table
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                display_name TEXT,
                created_at TEXT,
                last_sync TEXT,
                auth_token_path TEXT,
                config_json TEXT NOT NULL
            )
        """)
        
        # Metric data table
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS metric_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                data_date TEXT NOT NULL,
                data_json TEXT NOT NULL,
                checksum TEXT NOT NULL,
                stored_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                UNIQUE (user_id, metric_type, data_date)
            )
        """)
        
        # Sync status table
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS sync_status (
                user_id TEXT NOT NULL,
                sync_id TEXT NOT NULL,
                status_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, sync_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        """)
        
        # Sync checkpoints table
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS sync_checkpoints (
                user_id TEXT NOT NULL,
                sync_id TEXT NOT NULL,
                checkpoint_json TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                PRIMARY KEY (user_id, sync_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for better performance
        self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_metric_data_user_metric 
            ON metric_data (user_id, metric_type)
        """)
        
        self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_metric_data_user_date 
            ON metric_data (user_id, data_date)
        """)
        
        self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sync_status_user 
            ON sync_status (user_id)
        """)
        
        self._db.commit()
    
    @contextmanager
    def transaction(self, user_id: str):
        """Context manager for database transactions with user-level locking."""
        if user_id not in self._transaction_locks:
            self._transaction_locks[user_id] = threading.Lock()
        
        lock = self._transaction_locks[user_id]
        if not lock.acquire(timeout=30):  # 30 second timeout
            raise LockError(f"Failed to acquire transaction lock for user {user_id}")
        
        try:
            if self._db is None:
                raise LocalDBError("Database not open")
            
            self._db.execute("BEGIN IMMEDIATE")
            try:
                yield self._db
                self._db.commit()
            except Exception:
                self._db.rollback()
                raise
        finally:
            lock.release()
    
    def _load_users(self) -> None:
        """Load user configurations from database."""
        if self._db is None:
            return
        
        self._users_cache.clear()
        
        cursor = self._db.execute("SELECT user_id, config_json FROM users")
        for user_id, config_json in cursor.fetchall():
            try:
                user_data = json.loads(config_json)
                self._users_cache[user_id] = UserConfig.from_dict(user_data)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to load user config for {user_id}: {e}")
    
    def add_user(self, user_config: UserConfig) -> None:
        """Add a new user configuration."""
        with self._lock:
            if self._db is None:
                raise LocalDBError("Database not open")
            
            # Check if user already exists
            if user_config.user_id in self._users_cache:
                raise LocalDBError(f"User {user_config.user_id} already exists")
            
            # Set created_at if not set
            if user_config.created_at is None:
                user_config.created_at = datetime.now()
            
            with self.transaction(user_config.user_id):
                self._db.execute("""
                    INSERT INTO users (
                        user_id, email, display_name, created_at, 
                        last_sync, auth_token_path, config_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_config.user_id,
                    user_config.email,
                    user_config.display_name,
                    user_config.created_at.isoformat() if user_config.created_at else None,
                    user_config.last_sync.isoformat() if user_config.last_sync else None,
                    user_config.auth_token_path,
                    json.dumps(user_config.to_dict()),
                ))
            
            # Update cache
            self._users_cache[user_config.user_id] = user_config
    
    def get_user(self, user_id: str) -> UserConfig:
        """Get user configuration."""
        with self._lock:
            if user_id not in self._users_cache:
                raise UserNotFoundError(f"User {user_id} not found")
            return self._users_cache[user_id]
    
    def update_user(self, user_config: UserConfig) -> None:
        """Update user configuration."""
        with self._lock:
            if self._db is None:
                raise LocalDBError("Database not open")
            
            if user_config.user_id not in self._users_cache:
                raise UserNotFoundError(f"User {user_config.user_id} not found")
            
            with self.transaction(user_config.user_id):
                self._db.execute("""
                    UPDATE users SET 
                        email = ?, display_name = ?, created_at = ?,
                        last_sync = ?, auth_token_path = ?, config_json = ?
                    WHERE user_id = ?
                """, (
                    user_config.email,
                    user_config.display_name,
                    user_config.created_at.isoformat() if user_config.created_at else None,
                    user_config.last_sync.isoformat() if user_config.last_sync else None,
                    user_config.auth_token_path,
                    json.dumps(user_config.to_dict()),
                    user_config.user_id,
                ))
            
            # Update cache
            self._users_cache[user_config.user_id] = user_config
    
    def list_users(self) -> List[UserConfig]:
        """List all users."""
        with self._lock:
            return list(self._users_cache.values())
    
    def remove_user(self, user_id: str) -> None:
        """Remove user and all their data."""
        with self._lock:
            if self._db is None:
                raise LocalDBError("Database not open")
            
            if user_id not in self._users_cache:
                raise UserNotFoundError(f"User {user_id} not found")
            
            with self.transaction(user_id):
                # Remove user (cascade will remove related data)
                self._db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            
            # Update cache
            del self._users_cache[user_id]
    
    def store_metric_data(
        self, 
        user_id: str, 
        metric_type: str, 
        data_date: Union[str, date], 
        data: Dict[str, Any]
    ) -> None:
        """Store metric data for a specific user and date."""
        if self._db is None:
            raise LocalDBError("Database not open")
        
        if user_id not in self._users_cache:
            raise UserNotFoundError(f"User {user_id} not found")
        
        # Convert date to string if needed
        if isinstance(data_date, date):
            date_str = data_date.isoformat()
        else:
            date_str = data_date
        
        # Ensure data is JSON serializable
        from .sync import _convert_to_dict
        serializable_data = _convert_to_dict(data)
        
        # Calculate checksum
        checksum = self._calculate_checksum(serializable_data)
        data_json = json.dumps(serializable_data, separators=(',', ':'))
        stored_at = datetime.now().isoformat()
        
        with self.transaction(user_id):
            self._db.execute("""
                INSERT OR REPLACE INTO metric_data (
                    user_id, metric_type, data_date, data_json, checksum, stored_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, metric_type, date_str, data_json, checksum, stored_at))
    
    def get_metric_data(
        self, 
        user_id: str, 
        metric_type: str, 
        data_date: Union[str, date]
    ) -> Optional[Dict[str, Any]]:
        """Get metric data for a specific user and date."""
        if self._db is None:
            raise LocalDBError("Database not open")
        
        if user_id not in self._users_cache:
            raise UserNotFoundError(f"User {user_id} not found")
        
        # Convert date to string if needed
        if isinstance(data_date, date):
            date_str = data_date.isoformat()
        else:
            date_str = data_date
        
        cursor = self._db.execute("""
            SELECT data_json, checksum FROM metric_data 
            WHERE user_id = ? AND metric_type = ? AND data_date = ?
        """, (user_id, metric_type, date_str))
        
        row = cursor.fetchone()
        if row is None:
            return None
        
        data_json, stored_checksum = row
        
        try:
            data = json.loads(data_json)
            
            # Verify data integrity
            if stored_checksum:
                calculated_checksum = self._calculate_checksum(data)
                if stored_checksum != calculated_checksum:
                    raise DataIntegrityError(
                        f"Data corruption detected for {user_id}:{metric_type}:{date_str}"
                    )
            
            return data
        except json.JSONDecodeError as e:
            raise DataIntegrityError(f"Failed to decode metric data: {e}")
    
    def list_metric_dates(
        self, 
        user_id: str, 
        metric_type: str,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None
    ) -> List[str]:
        """List available dates for a metric type."""
        if self._db is None:
            raise LocalDBError("Database not open")
        
        if user_id not in self._users_cache:
            raise UserNotFoundError(f"User {user_id} not found")
        
        query = """
            SELECT DISTINCT data_date FROM metric_data 
            WHERE user_id = ? AND metric_type = ?
        """
        params = [user_id, metric_type]
        
        if start_date:
            query += " AND data_date >= ?"
            params.append(str(start_date))
        
        if end_date:
            query += " AND data_date <= ?"
            params.append(str(end_date))
        
        query += " ORDER BY data_date"
        
        cursor = self._db.execute(query, params)
        return [row[0] for row in cursor.fetchall()]
    
    def list_user_metrics(self, user_id: str) -> List[str]:
        """List all metric types available for a user."""
        if self._db is None:
            raise LocalDBError("Database not open")
        
        if user_id not in self._users_cache:
            raise UserNotFoundError(f"User {user_id} not found")
        
        cursor = self._db.execute("""
            SELECT DISTINCT metric_type FROM metric_data 
            WHERE user_id = ? ORDER BY metric_type
        """, (user_id,))
        
        return [row[0] for row in cursor.fetchall()]
    
    def store_sync_status(self, user_id: str, sync_id: str, status: Dict[str, Any]) -> None:
        """Store sync status for recovery purposes."""
        if self._db is None:
            raise LocalDBError("Database not open")
        
        status_json = json.dumps(status, separators=(',', ':'))
        updated_at = datetime.now().isoformat()
        
        with self.transaction(user_id):
            self._db.execute("""
                INSERT OR REPLACE INTO sync_status (
                    user_id, sync_id, status_json, updated_at
                ) VALUES (?, ?, ?, ?)
            """, (user_id, sync_id, status_json, updated_at))
    
    def get_sync_status(self, user_id: str, sync_id: str) -> Optional[Dict[str, Any]]:
        """Get sync status."""
        if self._db is None:
            raise LocalDBError("Database not open")
        
        cursor = self._db.execute("""
            SELECT status_json FROM sync_status 
            WHERE user_id = ? AND sync_id = ?
        """, (user_id, sync_id))
        
        row = cursor.fetchone()
        if row is None:
            return None
        
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return None
    
    def store_sync_checkpoint(
        self, 
        user_id: str, 
        sync_id: str, 
        checkpoint: Dict[str, Any]
    ) -> None:
        """Store sync checkpoint for crash recovery."""
        if self._db is None:
            raise LocalDBError("Database not open")
        
        checkpoint_data = {
            "checkpoint": checkpoint,
            "timestamp": datetime.now().isoformat(),
            "sync_id": sync_id,
        }
        
        checkpoint_json = json.dumps(checkpoint_data, separators=(',', ':'))
        timestamp = datetime.now().isoformat()
        
        with self.transaction(user_id):
            self._db.execute("""
                INSERT OR REPLACE INTO sync_checkpoints (
                    user_id, sync_id, checkpoint_json, timestamp
                ) VALUES (?, ?, ?, ?)
            """, (user_id, sync_id, checkpoint_json, timestamp))
    
    def get_sync_checkpoint(self, user_id: str, sync_id: str) -> Optional[Dict[str, Any]]:
        """Get sync checkpoint for recovery."""
        if self._db is None:
            raise LocalDBError("Database not open")
        
        cursor = self._db.execute("""
            SELECT checkpoint_json FROM sync_checkpoints 
            WHERE user_id = ? AND sync_id = ?
        """, (user_id, sync_id))
        
        row = cursor.fetchone()
        if row is None:
            return None
        
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return None
    
    def cleanup_sync_data(self, user_id: str, sync_id: str) -> None:
        """Clean up sync status and checkpoint data after successful completion."""
        if self._db is None:
            raise LocalDBError("Database not open")
        
        with self.transaction(user_id):
            # Remove status
            self._db.execute("""
                DELETE FROM sync_status WHERE user_id = ? AND sync_id = ?
            """, (user_id, sync_id))
            
            # Remove checkpoint
            self._db.execute("""
                DELETE FROM sync_checkpoints WHERE user_id = ? AND sync_id = ?
            """, (user_id, sync_id))
    
    def cleanup_sync_checkpoint(self, user_id: str, sync_id: str) -> None:
        """Clean up only checkpoint data, keeping status for history."""
        if self._db is None:
            raise LocalDBError("Database not open")
        
        with self.transaction(user_id):
            # Remove only checkpoint, keep status
            self._db.execute("""
                DELETE FROM sync_checkpoints WHERE user_id = ? AND sync_id = ?
            """, (user_id, sync_id))
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        if self._db is None:
            raise LocalDBError("Database not open")
        
        stats = {
            "users_count": len(self._users_cache),
            "db_path": str(self.config.db_path),
            "compression_enabled": self.config.compression,
        }
        
        # Count data records per user
        user_stats = {}
        cursor = self._db.execute("""
            SELECT user_id, COUNT(*) FROM metric_data GROUP BY user_id
        """)
        
        for user_id, count in cursor.fetchall():
            user_stats[user_id] = count
        
        stats["user_data_counts"] = user_stats
        
        # Database size
        cursor = self._db.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
        row = cursor.fetchone()
        if row:
            stats["database_size_bytes"] = row[0]
        
        return stats
    
    def _calculate_checksum(self, data: Any) -> str:
        """Calculate checksum for data integrity verification."""
        data_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(data_json.encode("utf-8")).hexdigest()
    
    @staticmethod
    def generate_sync_id() -> str:
        """Generate a unique sync ID."""
        return str(uuid.uuid4())