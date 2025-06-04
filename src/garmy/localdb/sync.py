"""Data synchronization engine with crash recovery."""

import asyncio
import logging
from dataclasses import dataclass, field, asdict, is_dataclass
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Set
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..core.client import APIClient
from ..core.exceptions import GarmyError
from .config import SyncConfig
from .exceptions import SyncError, SyncInterruptedError
from .storage import LocalDataStore


class SyncStatus(Enum):
    """Sync operation status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass
class SyncProgress:
    """Progress information for sync operation."""
    
    sync_id: str
    user_id: str
    status: SyncStatus
    total_metrics: int
    completed_metrics: int
    total_days: int
    completed_days: int
    current_metric: Optional[str] = None
    current_date: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    estimated_completion: Optional[datetime] = None
    
    @property
    def progress_percentage(self) -> float:
        """Calculate overall progress percentage."""
        if self.total_days == 0:
            return 0.0
        return (self.completed_days / self.total_days) * 100
    
    @property
    def metric_progress_percentage(self) -> float:
        """Calculate metric progress percentage."""
        if self.total_metrics == 0:
            return 0.0
        return (self.completed_metrics / self.total_metrics) * 100
    
    @property
    def elapsed_time(self) -> Optional[timedelta]:
        """Calculate elapsed time."""
        if self.started_at is None:
            return None
        end_time = self.completed_at or datetime.now()
        return end_time - self.started_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "sync_id": self.sync_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "total_metrics": self.total_metrics,
            "completed_metrics": self.completed_metrics,
            "total_days": self.total_days,
            "completed_days": self.completed_days,
            "current_metric": self.current_metric,
            "current_date": self.current_date,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncProgress":
        """Create from dictionary."""
        return cls(
            sync_id=data["sync_id"],
            user_id=data["user_id"],
            status=SyncStatus(data["status"]),
            total_metrics=data["total_metrics"],
            completed_metrics=data["completed_metrics"],
            total_days=data["total_days"],
            completed_days=data["completed_days"],
            current_metric=data.get("current_metric"),
            current_date=data.get("current_date"),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error_message=data.get("error_message"),
            retry_count=data.get("retry_count", 0),
            estimated_completion=datetime.fromisoformat(data["estimated_completion"]) if data.get("estimated_completion") else None,
        )


@dataclass
class SyncCheckpoint:
    """Checkpoint data for crash recovery."""
    
    sync_id: str
    user_id: str
    completed_dates: Set[str] = field(default_factory=set)  # set of completed date strings
    failed_attempts: Dict[str, int] = field(default_factory=dict)  # "metric:date" -> attempt count
    last_checkpoint: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "sync_id": self.sync_id,
            "user_id": self.user_id,
            "completed_dates": list(self.completed_dates),
            "failed_attempts": self.failed_attempts,
            "last_checkpoint": self.last_checkpoint.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncCheckpoint":
        """Create from dictionary."""
        return cls(
            sync_id=data["sync_id"],
            user_id=data["user_id"],
            completed_dates=set(data.get("completed_dates", [])),
            failed_attempts=data.get("failed_attempts", {}),
            last_checkpoint=datetime.fromisoformat(data["last_checkpoint"]),
        )


def _convert_to_dict(obj: Any) -> Any:
    """Convert dataclass objects to dictionaries recursively."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    elif isinstance(obj, dict):
        return {key: _convert_to_dict(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_to_dict(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(_convert_to_dict(item) for item in obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    else:
        return obj


class SyncManager:
    """Manages data synchronization with crash recovery."""
    
    def __init__(
        self, 
        api_client: APIClient, 
        storage: LocalDataStore,
        max_workers: int = 4,
        checkpoint_interval: int = 60,  # seconds
    ) -> None:
        self.api_client = api_client
        self.storage = storage
        self.max_workers = max_workers
        self.checkpoint_interval = checkpoint_interval
        self.logger = logging.getLogger(__name__)
        
        # Active sync tracking
        self._active_syncs: Dict[str, SyncProgress] = {}
        self._sync_tasks: Dict[str, asyncio.Task] = {}
        self._progress_callbacks: List[Callable[[SyncProgress], None]] = []
        self._stop_flags: Dict[str, bool] = {}
    
    def add_progress_callback(self, callback: Callable[[SyncProgress], None]) -> None:
        """Add callback for progress updates."""
        self._progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[SyncProgress], None]) -> None:
        """Remove progress callback."""
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)
    
    def _notify_progress(self, progress: SyncProgress) -> None:
        """Notify all callbacks of progress update."""
        for callback in self._progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                self.logger.warning(f"Progress callback failed: {e}")
    
    async def start_sync(self, config: SyncConfig, resume: bool = True) -> str:
        """Start data synchronization."""
        sync_id = LocalDataStore.generate_sync_id()
        
        # Check for existing interrupted sync
        if resume:
            existing_sync = await self._find_interrupted_sync(config.user_id)
            if existing_sync:
                sync_id = existing_sync
                self.logger.info(f"Resuming interrupted sync {sync_id}")
        
        # Create progress tracker
        progress = await self._initialize_sync_progress(sync_id, config)
        self._active_syncs[sync_id] = progress
        self._stop_flags[sync_id] = False
        
        # Start sync task with error handling
        task = asyncio.create_task(self._run_sync_with_error_handling(sync_id, config))
        self._sync_tasks[sync_id] = task
        
        return sync_id
    
    async def pause_sync(self, sync_id: str) -> None:
        """Pause a running sync operation."""
        if sync_id in self._active_syncs:
            progress = self._active_syncs[sync_id]
            if progress.status == SyncStatus.RUNNING:
                progress.status = SyncStatus.PAUSED
                self._stop_flags[sync_id] = True
                await self._update_progress(progress)
    
    async def resume_sync(self, sync_id: str) -> None:
        """Resume a paused sync operation."""
        if sync_id in self._active_syncs:
            progress = self._active_syncs[sync_id]
            if progress.status == SyncStatus.PAUSED:
                progress.status = SyncStatus.RUNNING
                self._stop_flags[sync_id] = False
                await self._update_progress(progress)
    
    async def stop_sync(self, sync_id: str) -> None:
        """Stop a sync operation."""
        self._stop_flags[sync_id] = True
        
        if sync_id in self._sync_tasks:
            task = self._sync_tasks[sync_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    
    def get_sync_progress(self, sync_id: str) -> Optional[SyncProgress]:
        """Get current sync progress."""
        if sync_id in self._active_syncs:
            return self._active_syncs[sync_id]
        
        # Try loading from storage - need to iterate through all users
        for user_config in self.storage.list_users():
            status_data = self.storage.get_sync_status(user_config.user_id, sync_id)
            if status_data:
                return SyncProgress.from_dict(status_data)
        
        return None
    
    def list_active_syncs(self) -> List[SyncProgress]:
        """List all active sync operations."""
        return list(self._active_syncs.values())
    
    async def _find_interrupted_sync(self, user_id: str) -> Optional[str]:
        """Find interrupted sync for user."""
        # This would iterate through sync status records to find interrupted syncs
        # For now, return None - this can be enhanced later
        return None
    
    async def _initialize_sync_progress(self, sync_id: str, config: SyncConfig) -> SyncProgress:
        """Initialize sync progress tracking."""
        # Calculate total work
        start_date = config.start_date
        end_date = config.end_date
        total_days = (end_date - start_date).days + 1
        total_metrics = len(config.metrics)
        
        # Check for existing checkpoint
        checkpoint_data = self.storage.get_sync_checkpoint(config.user_id, sync_id)
        completed_days = 0
        
        if checkpoint_data:
            checkpoint = SyncCheckpoint.from_dict(checkpoint_data["checkpoint"])
            completed_days = len(checkpoint.completed_dates)
        
        progress = SyncProgress(
            sync_id=sync_id,
            user_id=config.user_id,
            status=SyncStatus.PENDING,
            total_metrics=total_metrics,
            completed_metrics=0,  # Not tracking by metrics anymore
            total_days=total_days,
            completed_days=completed_days,
            started_at=datetime.now(),
        )
        
        await self._update_progress(progress)
        return progress
    
    async def _run_sync_with_error_handling(self, sync_id: str, config: SyncConfig) -> None:
        """Wrapper around _run_sync with guaranteed error handling."""
        try:
            await self._run_sync(sync_id, config)
        except Exception as e:
            # Guaranteed fallback error handling
            self.logger.error(f"Unexpected error in sync {sync_id}: {e}", exc_info=True)
            
            # Ensure progress status is updated
            if sync_id in self._active_syncs:
                progress = self._active_syncs[sync_id]
                progress.status = SyncStatus.FAILED
                progress.error_message = f"Unexpected error: {str(e)}"
                progress.completed_at = datetime.now()
                await self._update_progress(progress)
            
            # Clean up
            if sync_id in self._active_syncs:
                del self._active_syncs[sync_id]
            if sync_id in self._sync_tasks:
                del self._sync_tasks[sync_id]
            if sync_id in self._stop_flags:
                del self._stop_flags[sync_id]
    
    async def _run_sync(self, sync_id: str, config: SyncConfig) -> None:
        """Run the synchronization process."""
        self.logger.info(f"Starting sync {sync_id} for user {config.user_id}")
        progress = self._active_syncs[sync_id]
        checkpoint = await self._load_or_create_checkpoint(sync_id, config)
        self.logger.info(f"Loaded checkpoint for sync {sync_id}: {len(checkpoint.completed_dates)} completed dates")
        
        try:
            progress.status = SyncStatus.RUNNING
            await self._update_progress(progress)
            self.logger.info(f"Sync {sync_id} status updated to RUNNING")
            
            # Generate date range
            current_date = config.start_date
            dates = []
            while current_date <= config.end_date:
                dates.append(current_date)
                current_date += timedelta(days=1)
            
            # Reverse order if configured (newest first - default behavior)
            if config.reverse_chronological:
                dates.reverse()
            
            # Process dates in batches
            batch_size = config.batch_size
            for i in range(0, len(dates), batch_size):
                if self._stop_flags.get(sync_id, False):
                    progress.status = SyncStatus.PAUSED
                    await self._update_progress(progress)
                    return
                
                batch_dates = dates[i:i + batch_size]
                
                # Filter out already completed dates
                pending_dates = [d for d in batch_dates if d.isoformat() not in checkpoint.completed_dates]
                
                if not pending_dates:
                    continue
                
                # Process batch of dates
                await self._process_date_batch(sync_id, config, pending_dates, checkpoint)
            
            # Sync completed successfully
            progress.status = SyncStatus.COMPLETED
            progress.completed_at = datetime.now()
            progress.current_metric = None
            progress.current_date = None
            
            await self._update_progress(progress)
            
            # Clean up only checkpoint data, keep status for history
            self.storage.cleanup_sync_checkpoint(config.user_id, sync_id)
            
            # Keep in active syncs for a bit so status can be seen
            await asyncio.sleep(2)
            
        except Exception as e:
            self.logger.error(f"Sync {sync_id} failed: {e}", exc_info=True)
            progress.status = SyncStatus.FAILED
            progress.error_message = str(e)
            await self._update_progress(progress)
            
            # Save checkpoint for potential recovery
            await self._save_checkpoint(checkpoint)
            
            # Don't remove from active syncs immediately so we can see the error
            return
            
        finally:
            # Clean up
            if sync_id in self._active_syncs:
                del self._active_syncs[sync_id]
            if sync_id in self._sync_tasks:
                del self._sync_tasks[sync_id]
            if sync_id in self._stop_flags:
                del self._stop_flags[sync_id]
    
    async def _process_date_batch(
        self,
        sync_id: str,
        config: SyncConfig,
        dates: List[date],
        checkpoint: SyncCheckpoint
    ) -> None:
        """Process a batch of dates, downloading all metrics for each date."""
        progress = self._active_syncs[sync_id]
        
        for date_obj in dates:
            if self._stop_flags.get(sync_id, False):
                return
            
            date_str = date_obj.isoformat()
            progress.current_date = date_str
            await self._update_progress(progress)
            
            # Download all metrics for this date
            date_success = True
            for metric in config.metrics:
                if self._stop_flags.get(sync_id, False):
                    return
                
                progress.current_metric = metric
                await self._update_progress(progress)
                
                success = await self._sync_single_metric_date(
                    sync_id, config, metric, date_str, checkpoint
                )
                
                if not success:
                    date_success = False
            
            # Mark date as completed only if all metrics succeeded or were skipped
            if date_success:
                checkpoint.completed_dates.add(date_str)
                progress.completed_days += 1
                
                # Save checkpoint periodically
                if len(checkpoint.completed_dates) % 10 == 0:  # Every 10 dates
                    await self._save_checkpoint(checkpoint)
                
                await self._update_progress(progress)
    
    async def _sync_single_metric_date(
        self,
        sync_id: str,
        config: SyncConfig,
        metric: str,
        date_str: str,
        checkpoint: SyncCheckpoint
    ) -> bool:
        """Sync a single metric for a single date with retry logic."""
        retry_key = f"{metric}:{date_str}"
        attempts = checkpoint.failed_attempts.get(retry_key, 0)
        
        if attempts >= config.retry_attempts:
            self.logger.warning(f"Skipping {retry_key} after {attempts} failed attempts")
            return True  # Consider as success to not block the date
        
        for attempt in range(attempts, config.retry_attempts):
            try:
                # Fetch data from API
                metric_accessor = self.api_client.metrics.get(metric)
                data = metric_accessor.get(date_str)
                
                if data is not None:
                    # Convert dataclass to dict if needed
                    data_dict = _convert_to_dict(data)
                    
                    # Store in local database
                    self.storage.store_metric_data(
                        config.user_id, metric, date_str, data_dict
                    )
                    
                    # Remove from failed attempts
                    if retry_key in checkpoint.failed_attempts:
                        del checkpoint.failed_attempts[retry_key]
                    
                    return True
                else:
                    self.logger.debug(f"No data available for {metric} on {date_str}")
                    return True  # No data is considered success
                    
            except TypeError as e:
                # Data parsing/structure errors - don't retry, just skip
                if "missing" in str(e) and "required positional argument" in str(e):
                    self.logger.warning(f"Data structure error for {retry_key}, skipping: {e}")
                    return True  # Skip this metric for this date
                else:
                    # Other TypeError, treat as retryable
                    self.logger.warning(f"Attempt {attempt + 1} failed for {retry_key}: {e}")
                    checkpoint.failed_attempts[retry_key] = attempt + 1
                    if attempt < config.retry_attempts - 1:
                        await asyncio.sleep(config.retry_delay)
            
            except (ValueError, AttributeError) as e:
                # Data validation errors - don't retry, just skip
                self.logger.warning(f"Data validation error for {retry_key}, skipping: {e}")
                return True  # Skip this metric for this date
                    
            except Exception as e:
                # Network or other retryable errors
                self.logger.warning(f"Attempt {attempt + 1} failed for {retry_key}: {e}")
                checkpoint.failed_attempts[retry_key] = attempt + 1
                
                if attempt < config.retry_attempts - 1:
                    await asyncio.sleep(config.retry_delay)
        
        self.logger.error(f"Failed to sync {retry_key} after {config.retry_attempts} attempts")
        return False  # This metric failed for this date
    
    async def _load_or_create_checkpoint(self, sync_id: str, config: SyncConfig) -> SyncCheckpoint:
        """Load existing checkpoint or create new one."""
        checkpoint_data = self.storage.get_sync_checkpoint(config.user_id, sync_id)
        
        if checkpoint_data:
            return SyncCheckpoint.from_dict(checkpoint_data["checkpoint"])
        else:
            return SyncCheckpoint(sync_id=sync_id, user_id=config.user_id)
    
    async def _save_checkpoint(self, checkpoint: SyncCheckpoint) -> None:
        """Save checkpoint to storage."""
        checkpoint.last_checkpoint = datetime.now()
        self.storage.store_sync_checkpoint(
            checkpoint.user_id, 
            checkpoint.sync_id, 
            checkpoint.to_dict()
        )
    
    async def _update_progress(self, progress: SyncProgress) -> None:
        """Update progress in storage and notify callbacks."""
        # Calculate estimated completion
        if progress.status == SyncStatus.RUNNING and progress.completed_days > 0:
            elapsed = progress.elapsed_time
            if elapsed:
                rate = progress.completed_days / elapsed.total_seconds()
                remaining_days = progress.total_days - progress.completed_days
                remaining_seconds = remaining_days / rate if rate > 0 else 0
                progress.estimated_completion = datetime.now() + timedelta(seconds=remaining_seconds)
        
        # Store in database
        self.storage.store_sync_status(
            progress.user_id, 
            progress.sync_id, 
            progress.to_dict()
        )
        
        # Notify callbacks
        self._notify_progress(progress)