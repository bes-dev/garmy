"""Data synchronization manager."""

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

from .storage import LocalDataStore
from ..core.client import APIClient


@dataclass
class SyncProgress:
    """Sync operation progress."""
    sync_id: str
    user_id: str
    status: str  # 'running', 'completed', 'failed', 'paused'
    current_metric: str
    current_date: str
    total_metrics: int
    completed_metrics: int
    total_dates: int
    completed_dates: int
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    
    @property
    def progress_percentage(self) -> float:
        """Calculate overall progress percentage (day-by-day approach)."""
        if self.total_dates == 0 or self.total_metrics == 0:
            return 0.0
        
        # Progress based on total operations (days * metrics)
        total_operations = self.total_dates * self.total_metrics
        if total_operations == 0:
            return 0.0
            
        # Use completed_metrics which now tracks total operations
        return (self.completed_metrics / total_operations) * 100
    
    @property
    def elapsed_time(self) -> timedelta:
        """Get elapsed time."""
        end = self.end_time or datetime.utcnow()
        return end - self.start_time


class SyncManager:
    """Manages data synchronization between Garmin API and local database."""
    
    def __init__(self, api_client: APIClient, storage: LocalDataStore, user_id: str):
        self.api_client = api_client
        self.storage = storage
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)
        self._active_syncs: Dict[str, SyncProgress] = {}
        self._existing_data_cache: Dict[str, set] = {}  # Cache existing dates per metric
    
    def _get_available_metrics(self) -> List[str]:
        """Get all available metrics using auto-discovery."""
        try:
            if hasattr(self.api_client, 'metrics'):
                # Get ALL metrics from garmy's auto-discovery
                all_metrics = list(self.api_client.metrics.keys())
                
                self.logger.info(f"Auto-discovered {len(all_metrics)} metrics: {', '.join(all_metrics)}")
                
                return all_metrics
            else:
                # Fallback if metrics discovery fails
                fallback_metrics = ['steps', 'heart_rate', 'sleep', 'body_battery']
                self.logger.warning("API client doesn't have metrics discovery, using fallback metrics")
                return fallback_metrics
        
        except Exception as e:
            self.logger.error(f"Error discovering metrics: {e}")
            # Use minimal safe set as fallback
            return ['steps', 'heart_rate', 'sleep']

    def _build_existing_data_cache(self, start_date: date, end_date: date) -> List[str]:
        """Build cache of existing data for efficient skip checks. Returns available metrics."""
        self._existing_data_cache.clear()
        
        # Get all available metrics using auto-discovery
        available_metrics = self._get_available_metrics()
        
        if not available_metrics:
            self.logger.warning("No available metrics found for synchronization")
            return []
        
        for metric_type in available_metrics:
            # Single query to get ALL existing dates for this metric in the range
            existing_dates = self.storage.list_metric_dates(
                self.user_id, metric_type, start_date, end_date
            )
            # Convert to set of date objects for O(1) lookup
            self._existing_data_cache[metric_type] = {
                datetime.strptime(date_str, "%Y-%m-%d").date() 
                for date_str in existing_dates
            }
            self.logger.debug(f"Cached {len(existing_dates)} existing dates for {metric_type}")
        
        return available_metrics
    
    def _should_skip_date(self, metric_type: str, sync_date: date) -> bool:
        """Check if date should be skipped (O(1) lookup)."""
        return sync_date in self._existing_data_cache.get(metric_type, set())
    
    def get_sync_efficiency_stats(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get statistics about sync efficiency without actually syncing."""
        available_metrics = self._build_existing_data_cache(start_date, end_date)
        
        if not available_metrics:
            return {
                'error': 'No available metrics found for synchronization',
                'suggestion': 'Check API client authentication and connectivity'
            }
        
        # Calculate date range
        total_days = (end_date - start_date).days + 1
        total_operations = total_days * len(available_metrics)
        
        # Count existing data
        existing_operations = 0
        missing_operations = 0
        
        current_date = start_date
        while current_date <= end_date:
            for metric_type in available_metrics:
                if self._should_skip_date(metric_type, current_date):
                    existing_operations += 1
                else:
                    missing_operations += 1
            current_date += timedelta(days=1)
        
        efficiency_percentage = (existing_operations / total_operations) * 100 if total_operations > 0 else 0
        
        return {
            'total_operations': total_operations,
            'existing_operations': existing_operations,
            'missing_operations': missing_operations,
            'skip_efficiency': round(efficiency_percentage, 1),
            'api_calls_saved': existing_operations,
            'api_calls_needed': missing_operations,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': total_days
            },
            'metrics': {
                metric_type: len(self._existing_data_cache.get(metric_type, set()))
                for metric_type in available_metrics
            },
            'available_metrics': available_metrics
        }

    async def sync_all_metrics(self, start_date: date, end_date: date, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Sync ALL available metrics for a date range using day-by-day strategy."""
        sync_id = f"{self.user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Build cache of existing data for efficient skip checks and get available metrics
        all_available_metrics = self._build_existing_data_cache(start_date, end_date)
        
        # Exclude activities from regular metrics sync (activities are handled separately)
        available_metrics = [m for m in all_available_metrics if m != 'activities']
        
        if not available_metrics:
            return {
                'error': 'No available metrics found for synchronization',
                'suggestion': 'Check API client authentication and connectivity'
            }
        
        # Calculate date range (newest to oldest)
        date_range = []
        current_date = end_date
        while current_date >= start_date:
            date_range.append(current_date)
            current_date -= timedelta(days=1)
        
        # Initialize progress
        progress = SyncProgress(
            sync_id=sync_id,
            user_id=self.user_id,
            status='running',
            current_metric='',
            current_date='',
            total_metrics=len(available_metrics),
            completed_metrics=0,
            total_dates=len(date_range),
            completed_dates=0,
            start_time=datetime.utcnow()
        )
        
        self._active_syncs[sync_id] = progress
        
        try:
            results = {
                'sync_id': sync_id,
                'metrics_synced': {metric: {'records_synced': 0, 'records_updated': 0, 'records_skipped': 0, 'errors': []} for metric in available_metrics},
                'total_records': 0,
                'errors': [],
                'available_metrics': available_metrics
            }
            
            # Sync day by day (newest to oldest)
            for date_idx, sync_date in enumerate(date_range):
                progress.current_date = sync_date.isoformat()
                
                self.logger.info(f"Syncing all metrics for {sync_date}")
                
                # Sync all metrics for this date
                for metric_idx, metric_type in enumerate(available_metrics):
                    progress.current_metric = metric_type
                    
                    # Calculate overall progress: (completed_days * total_metrics + current_metric) / (total_days * total_metrics)
                    total_operations = len(date_range) * len(available_metrics)
                    completed_operations = date_idx * len(available_metrics) + metric_idx
                    progress.completed_dates = date_idx
                    progress.completed_metrics = completed_operations
                    
                    if progress_callback:
                        progress_callback(progress)
                    
                    try:
                        # Check if we should skip this date (O(1) lookup)
                        if self._should_skip_date(metric_type, sync_date):
                            results['metrics_synced'][metric_type]['records_skipped'] += 1
                            self.logger.debug(f"Skipping {metric_type} for {sync_date} - already exists")
                            continue
                        
                        # Get metric accessor
                        if not hasattr(self.api_client, 'metrics'):
                            raise ValueError("API client doesn't have metrics attribute")
                        
                        metric_accessor = self.api_client.metrics.get(metric_type)
                        if not metric_accessor:
                            self.logger.warning(f"Metric accessor for '{metric_type}' not found")
                            continue
                        
                        # Fetch new data from API (only if not skipped)
                        api_data = await self._fetch_metric_data(metric_accessor, sync_date)
                        
                        if api_data:
                            try:
                                # Store the data
                                self.storage.store_metric(self.user_id, metric_type, sync_date, api_data)
                                
                                # Since we skipped existing data, this is always a new record
                                results['metrics_synced'][metric_type]['records_synced'] += 1
                                results['total_records'] += 1
                                
                                # Update cache to avoid re-fetching this date in same session
                                if metric_type not in self._existing_data_cache:
                                    self._existing_data_cache[metric_type] = set()
                                self._existing_data_cache[metric_type].add(sync_date)
                                
                            except Exception as store_error:
                                error_msg = f"Error storing {metric_type} for {sync_date}: {store_error}"
                                results['metrics_synced'][metric_type]['errors'].append(error_msg)
                                results['errors'].append(error_msg)
                                self.logger.warning(error_msg)
                                results['metrics_synced'][metric_type]['records_skipped'] += 1
                        else:
                            results['metrics_synced'][metric_type]['records_skipped'] += 1
                            self.logger.debug(f"No {metric_type} data for {sync_date}")
                    
                    except Exception as e:
                        error_msg = f"Error syncing {metric_type} for {sync_date}: {e}"
                        results['metrics_synced'][metric_type]['errors'].append(error_msg)
                        results['errors'].append(error_msg)
                        self.logger.warning(error_msg)
                    
                    # Update progress after processing metric
                    progress.completed_metrics = date_idx * len(available_metrics) + metric_idx + 1
                    if progress_callback:
                        progress_callback(progress)
                
                # Small delay between days to avoid overwhelming the API
                await asyncio.sleep(0.2)
            
            progress.completed_dates = len(date_range)
            progress.status = 'completed'
            progress.end_time = datetime.utcnow()
            
            # Update user's last sync time
            self.storage.update_last_sync(self.user_id)
            
            return results
        
        except Exception as e:
            progress.status = 'failed'
            progress.error_message = str(e)
            progress.end_time = datetime.utcnow()
            self.logger.error(f"Sync failed for user {self.user_id}: {e}")
            raise
        
        finally:
            if progress_callback:
                progress_callback(progress)
    
    
    async def _fetch_metric_data(self, metric_accessor, sync_date: date) -> Optional[Any]:
        """Fetch data for a specific date from metric accessor."""
        try:
            # Convert date to string format expected by API
            date_str = sync_date.isoformat()
            
            # Try to get data for specific date
            # Most metric accessors support .get(date_string)
            data = metric_accessor.get(date_str)
            
            # Handle different return types
            if hasattr(data, 'daily_steps') and data.daily_steps:
                # Steps data - return the daily data for this specific date
                for daily_step in data.daily_steps:
                    if daily_step.calendar_date == date_str:
                        return daily_step
                return None
            
            elif hasattr(data, 'heart_rate_summary'):
                # Heart rate data
                return data.heart_rate_summary
            
            elif hasattr(data, 'sleep_summary'):
                # Sleep data
                return data.sleep_summary
            
            
            elif hasattr(data, 'body_battery_readings'):
                # Body battery data - need to transform to summary
                if not data.body_battery_readings:
                    return None
                
                readings = data.body_battery_readings
                levels = [r.level for r in readings]
                
                # Create summary object with proper charging/draining analysis
                from dataclasses import dataclass
                
                @dataclass
                class BodyBatterySummary:
                    calendar_date: str
                    start_level: int
                    end_level: int
                    highest_level: int
                    lowest_level: int
                    net_change: int
                    charging_periods_count: int
                    draining_periods_count: int
                    total_readings: int
                    readings_json: str
                
                # Analyze charging vs draining periods
                charging_count = 0
                draining_count = 0
                
                for reading in readings:
                    status = str(getattr(reading, 'status', '')).lower()
                    if 'charg' in status:
                        charging_count += 1
                    else:
                        draining_count += 1
                
                return BodyBatterySummary(
                    calendar_date=date_str,
                    start_level=readings[0].level,
                    end_level=readings[-1].level,
                    highest_level=max(levels),
                    lowest_level=min(levels),
                    net_change=readings[-1].level - readings[0].level,
                    charging_periods_count=charging_count,
                    draining_periods_count=draining_count,
                    total_readings=len(readings),
                    readings_json=str([{
                        'timestamp': r.datetime.isoformat() if hasattr(r, 'datetime') else '',
                        'level': r.level,
                        'status': str(getattr(r, 'status', ''))
                    } for r in readings])
                )
            
            else:
                # Direct data return
                return data
        
        except Exception as e:
            self.logger.warning(f"Failed to fetch {metric_accessor} data for {sync_date}: {e}")
            return None
    
    def get_sync_progress(self, sync_id: str) -> Optional[SyncProgress]:
        """Get progress of a sync operation."""
        return self._active_syncs.get(sync_id)
    
    def list_active_syncs(self) -> List[SyncProgress]:
        """List all active sync operations."""
        return list(self._active_syncs.values())
    
    def cancel_sync(self, sync_id: str) -> bool:
        """Cancel a sync operation."""
        if sync_id in self._active_syncs:
            progress = self._active_syncs[sync_id]
            progress.status = 'cancelled'
            progress.end_time = datetime.utcnow()
            return True
        return False
    
    async def sync_with_activities(self, start_date: date, end_date: date, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Sync ALL available metrics including activities."""
        self.logger.info(f"Starting full sync (metrics + activities) from {start_date} to {end_date}")
        
        # Sync regular metrics first
        result = await self.sync_all_metrics(start_date, end_date, progress_callback)
        
        # Check if activities are available and sync them separately
        available_metrics = self._get_available_metrics()
        if 'activities' in available_metrics:
            self.logger.info("Starting activities sync with pagination")
            activities_result = await self.sync_activities(start_date, end_date, progress_callback)
            
            # Merge results
            if 'metrics_synced' in result:
                result['metrics_synced']['activities'] = activities_result
                result['total_records'] += activities_result.get('records_synced', 0)
                if activities_result.get('errors'):
                    result['errors'].extend(activities_result['errors'])
            else:
                # If main sync failed, just return activities result
                result = {
                    'sync_id': f"{self.user_id}_activities_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    'metrics_synced': {'activities': activities_result},
                    'total_records': activities_result.get('records_synced', 0),
                    'errors': activities_result.get('errors', []),
                    'available_metrics': ['activities']
                }
        
        return result
    
    async def sync_recent_data(self, days: int = 30, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Sync recent data for all available metrics."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days-1)
        
        self.logger.info(f"Starting recent data sync for last {days} days")
        return await self.sync_with_activities(start_date, end_date, progress_callback)
    
    def _build_existing_activities_cache(self, start_date: date, end_date: date) -> set:
        """Build cache of existing activity IDs for efficient skip checks."""
        # Get all activities in date range and extract activity_ids
        activities = self.storage.get_activities_for_date_range(self.user_id, start_date, end_date)
        activity_ids = {activity.activity_id for activity in activities}
        self.logger.debug(f"Cached {len(activity_ids)} existing activity IDs")
        return activity_ids

    async def sync_activities(self, start_date: date, end_date: date, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Sync activities using pagination with date filtering."""
        result = {
            'records_synced': 0,
            'records_updated': 0,
            'records_skipped': 0,
            'errors': []
        }
        
        try:
            # Build cache of existing activity IDs for efficient skip checks
            existing_activity_ids = self._build_existing_activities_cache(start_date, end_date)
            
            # Get activities accessor
            if not hasattr(self.api_client, 'metrics'):
                result['errors'].append("API client doesn't have metrics attribute")
                return result
            
            activities_accessor = self.api_client.metrics.get('activities')
            if not activities_accessor:
                result['errors'].append("Activities accessor not found")
                return result
            
            # Pagination loop
            start_offset = 0
            limit = 100
            total_processed = 0
            
            self.logger.info(f"Syncing activities from {start_date} to {end_date}")
            
            while True:
                try:
                    # Fetch page of activities
                    activities = activities_accessor.list(limit=limit, start=start_offset)
                    
                    if not activities:
                        self.logger.info(f"No more activities found at offset {start_offset}")
                        break
                    
                    page_synced = 0
                    page_skipped = 0
                    
                    for activity in activities:
                        total_processed += 1
                        
                        # Update progress
                        if progress_callback:
                            # Create dummy progress for activities
                            class ActivitiesProgress:
                                def __init__(self):
                                    self.current_metric = 'activities'
                                    self.current_date = f"страница {start_offset//limit + 1}"
                                    self.progress_percentage = 0  # Can't calculate without total
                                    self.completed_metrics = total_processed
                                    self.total_metrics = total_processed + 1
                                    self.total_dates = 1
                                    self.completed_dates = 0
                                    self.elapsed_time = timedelta(seconds=0)
                            
                            progress_callback(ActivitiesProgress())
                        
                        try:
                            activity_date_str = activity.start_date
                            if not activity_date_str:
                                page_skipped += 1
                                continue
                            
                            activity_date = datetime.strptime(activity_date_str, '%Y-%m-%d').date()
                            
                            # Filter by date range
                            if start_date <= activity_date <= end_date:
                                # Check if activity already exists (O(1) lookup)
                                if activity.activity_id in existing_activity_ids:
                                    result['records_skipped'] += 1
                                    self.logger.debug(f"Skipping activity {activity.activity_id} - already exists")
                                    continue
                                
                                # Store new activity
                                self.storage.store_activity(self.user_id, activity)
                                result['records_synced'] += 1
                                page_synced += 1
                                
                                # Update cache to avoid re-processing this activity in same session
                                existing_activity_ids.add(activity.activity_id)
                            else:
                                page_skipped += 1
                                
                        except Exception as e:
                            error_msg = f"Error processing activity {activity.activity_id}: {e}"
                            result['errors'].append(error_msg)
                            self.logger.warning(error_msg)
                    
                    self.logger.info(f"Page {start_offset//limit + 1}: processed {len(activities)}, synced {page_synced}, skipped {page_skipped}")
                    
                    # Check if we should continue
                    if len(activities) < limit:
                        self.logger.info(f"Last page reached (got {len(activities)} < {limit})")
                        break
                    
                    start_offset += limit
                    
                    # Safety break to avoid infinite loops
                    if start_offset > 10000:  # Max 10k activities
                        self.logger.warning("Hit safety limit of 10k activities")
                        break
                        
                    # Small delay between pages
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    error_msg = f"Error fetching activities page {start_offset//limit + 1}: {e}"
                    result['errors'].append(error_msg)
                    self.logger.error(error_msg)
                    break
            
            self.logger.info(f"Activities sync completed: {result['records_synced']} new, {result['records_updated']} updated")
            
        except Exception as e:
            error_msg = f"Activities sync failed: {e}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return result