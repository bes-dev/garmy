"""Progress reporting for sync operations."""

import logging
from datetime import date
from typing import Optional
from tqdm import tqdm


class ProgressReporter:
    """Simple progress reporter with date tracking."""

    def __init__(self, use_tqdm: bool = False):
        self.use_tqdm = use_tqdm
        self.logger = logging.getLogger("garmy.sync")
        self.pbar: Optional[tqdm] = None
        self.current_date = None

    def start_sync(self, total: int):
        """Start sync progress tracking."""
        if self.use_tqdm:
            self.pbar = tqdm(total=total)

    def task_complete(self, task: str, sync_date: date):
        """Mark task as completed."""
        msg = f"[{sync_date}] {task}"
        if self.pbar:
            self.pbar.update(1)
            if self.current_date != sync_date:
                self.current_date = sync_date
                self.pbar.set_description(f"Syncing {sync_date}")
        else:
            self.logger.info(msg)

    def task_skipped(self, task: str, sync_date: date):
        """Mark task as skipped."""
        msg = f"[{sync_date}] {task} (skipped)"
        if self.pbar:
            self.pbar.update(1)
            if self.current_date != sync_date:
                self.current_date = sync_date
                self.pbar.set_description(f"Syncing {sync_date}")
        else:
            self.logger.info(msg)

    def task_failed(self, task: str, sync_date: date):
        """Mark task as failed."""
        msg = f"[{sync_date}] {task} (failed)"
        if self.pbar:
            self.pbar.update(1)
            if self.current_date != sync_date:
                self.current_date = sync_date
                self.pbar.set_description(f"Syncing {sync_date}")
        else:
            self.logger.warning(msg)

    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)

    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
    
    def end_sync(self):
        """End sync progress tracking."""
        if self.pbar:
            self.pbar.close()