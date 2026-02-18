"""Activity pagination and iteration utilities."""

from datetime import date
from typing import Any, List, Optional
import asyncio


class ActivitiesIterator:
    """Iterator-based activities synchronization with automatic pagination."""
    
    def __init__(self, api_client, sync_config, progress_reporter):
        """Initialize activities iterator.
        
        Args:
            api_client: Garmin API client for data access
            sync_config: Sync configuration with batch sizes
            progress_reporter: Progress reporting interface
        """
        self.api_client = api_client
        self.sync_config = sync_config  
        self.progress = progress_reporter
        
        # Iterator state
        self.current_activity = None
        self.current_activity_date = None
        self.activities_cache = []
        self.batch_offset = 0
        self.has_more_data = True
    
    def initialize(self):
        """Initialize the iterator by loading first batch."""
        self._load_next_batch()
        self._advance_to_next_activity()
    
    def _load_next_batch(self) -> bool:
        """Load next batch of activities from API in ascending order (oldest first)."""
        if not self.has_more_data:
            return False

        try:
            batch_size = self.sync_config.activities_batch_size
            # Request activities in ascending order (oldest first) to match sync order
            activities_batch = self.api_client.metrics.get('activities').list(
                limit=batch_size,
                start=self.batch_offset,
                sort_order='asc'
            )

            if not activities_batch or len(activities_batch) == 0:
                self.has_more_data = False
                return False

            # Append to cache and update offset
            self.activities_cache.extend(activities_batch)
            self.batch_offset += len(activities_batch)

            # Check if we got less than requested (indicates end of data)
            if len(activities_batch) < batch_size:
                self.has_more_data = False

            return True

        except Exception as e:
            self.progress.warning(f"Failed to load activities batch at offset {self.batch_offset}: {e}")
            self.has_more_data = False
            return False
    
    def _advance_to_next_activity(self) -> bool:
        """Advance to next activity, loading batches as needed."""
        while True:
            # If cache is empty, try to load more
            if not self.activities_cache:
                if not self._load_next_batch():
                    self.current_activity = None
                    self.current_activity_date = None
                    return False
            
            # Get next activity from cache
            if self.activities_cache:
                self.current_activity = self.activities_cache.pop(0)
                self.current_activity_date = self._extract_activity_date(self.current_activity)
                return True
            else:
                # No more activities available
                self.current_activity = None
                self.current_activity_date = None
                return False
    
    def _extract_activity_date(self, activity) -> Optional[date]:
        """Extract activity date from various possible fields."""
        start_time = None
        
        # Try different attribute names for start time
        for attr in ['start_time_local', 'startTimeLocal', 'start_time', 'activityDate']:
            if hasattr(activity, attr):
                start_time = getattr(activity, attr)
                break
        
        if start_time:
            try:
                # Handle ISO string format
                if isinstance(start_time, str):
                    from datetime import datetime
                    start_time = start_time.replace('Z', '+00:00')
                    if '.' in start_time and '+' in start_time:
                        dt = datetime.fromisoformat(start_time)
                    else:
                        dt = datetime.fromisoformat(start_time)
                    return dt.date()
                elif hasattr(start_time, 'date'):
                    return start_time.date()
            except Exception:
                pass
        return None
    
    def get_activities_for_date(self, target_date: date) -> List[Any]:
        """Get all activities for a specific date.

        Note: Activities are loaded in ascending order (oldest first) from the API.
        """
        activities = []

        # Ensure we have a current activity
        if self.current_activity is None:
            if not self._advance_to_next_activity():
                return activities

        # Process activities while they match or are older than target_date
        while self.current_activity is not None:
            if self.current_activity_date is None:
                # Skip activities without dates
                if not self._advance_to_next_activity():
                    break
                continue

            if self.current_activity_date < target_date:
                # Activity is older than target - skip it
                if not self._advance_to_next_activity():
                    break
                continue

            elif self.current_activity_date == target_date:
                # Activity matches target date - collect it
                activities.append(self.current_activity)
                if not self._advance_to_next_activity():
                    break
                continue

            else:  # self.current_activity_date > target_date
                # Activity is newer than target - we're done for this date
                break

        return activities