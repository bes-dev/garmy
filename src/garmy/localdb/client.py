"""LocalDB client with analytics capabilities."""

import asyncio
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .storage import LocalDataStore
from .sync import SyncManager
from ..core.client import APIClient
from ..auth.client import AuthClient


class LocalDBClient:
    """Main LocalDB client with analytics and sync capabilities."""
    
    def __init__(self, db_path: Union[str, Path]):
        self.storage = LocalDataStore(db_path)
        self._sync_managers: Dict[str, SyncManager] = {}
        self._api_clients: Dict[str, APIClient] = {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def close(self):
        """Close client and cleanup resources."""
        self.storage.close()
        self._sync_managers.clear()
        self._api_clients.clear()
    
    # User management
    def add_user(self, user_id: str, email: str, display_name: str = None, auth_token_path: str = None) -> None:
        """Add a new user."""
        self.storage.add_user(user_id, email, display_name, auth_token_path)
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information."""
        return self.storage.get_user(user_id)
    
    def list_users(self) -> List[Dict[str, Any]]:
        """List all users."""
        return self.storage.list_users()
    
    def remove_user(self, user_id: str) -> None:
        """Remove user and all their data."""
        # Clean up managers
        if user_id in self._sync_managers:
            del self._sync_managers[user_id]
        if user_id in self._api_clients:
            del self._api_clients[user_id]
        
        self.storage.remove_user(user_id)
    
    # Data operations  
    def store_metric_data(self, user_id: str, metric_type: str, data_date: Union[str, date], dataclass_instance: Any) -> None:
        """Store metric data using dataclass."""
        self.storage.store_metric(user_id, metric_type, data_date, dataclass_instance)
    
    def get_metric_data(self, user_id: str, metric_type: str, data_date: Union[str, date]) -> Optional[Any]:
        """Get metric data as dataclass."""
        return self.storage.get_metric(user_id, metric_type, data_date)
    
    def list_metric_dates(self, user_id: str, metric_type: str, start_date: Optional[Union[str, date]] = None, end_date: Optional[Union[str, date]] = None) -> List[str]:
        """List available dates for a metric."""
        return self.storage.list_metric_dates(user_id, metric_type, start_date, end_date)
    
    def list_user_metrics(self, user_id: str) -> List[str]:
        """List available metrics for user."""
        return self.storage.list_user_metrics(user_id)
    
    # Analytics operations
    def get_steps_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get steps analytics for user."""
        end_date = date.today()
        start_date = date.today().replace(day=1) if days == 30 else date.fromordinal(end_date.toordinal() - days + 1)
        
        dates = self.list_metric_dates(user_id, 'steps', start_date, end_date)
        
        if not dates:
            return {'error': 'No steps data available'}
        
        # Get all steps data for the period
        steps_data = []
        for date_str in dates:
            data = self.get_metric_data(user_id, 'steps', date_str)
            if data:
                steps_data.append({
                    'date': date_str,
                    'steps': data.total_steps,
                    'goal': data.step_goal,
                    'distance_km': data.distance_km
                })
        
        if not steps_data:
            return {'error': 'No valid steps data found'}
        
        # Calculate analytics
        total_steps = sum(d['steps'] for d in steps_data)
        total_distance = sum(d['distance_km'] for d in steps_data)
        avg_steps = total_steps / len(steps_data)
        max_steps = max(d['steps'] for d in steps_data)
        min_steps = min(d['steps'] for d in steps_data)
        
        # Goal achievement
        goals_met = sum(1 for d in steps_data if d['goal'] > 0 and d['steps'] >= d['goal'])
        goal_percentage = (goals_met / len(steps_data)) * 100 if steps_data else 0
        
        # Activity levels
        high_activity = sum(1 for d in steps_data if d['steps'] >= 10000)
        moderate_activity = sum(1 for d in steps_data if 5000 <= d['steps'] < 10000)
        low_activity = sum(1 for d in steps_data if d['steps'] < 5000)
        
        return {
            'period': {'start': dates[0], 'end': dates[-1], 'days': len(dates)},
            'totals': {
                'steps': total_steps,
                'distance_km': round(total_distance, 2)
            },
            'averages': {
                'daily_steps': int(avg_steps),
                'daily_distance_km': round(total_distance / len(steps_data), 2)
            },
            'extremes': {
                'max_steps': max_steps,
                'min_steps': min_steps,
                'range': max_steps - min_steps
            },
            'goals': {
                'days_achieved': goals_met,
                'achievement_rate': round(goal_percentage, 1)
            },
            'activity_distribution': {
                'high_activity_days': high_activity,
                'moderate_activity_days': moderate_activity,
                'low_activity_days': low_activity
            },
            'raw_data': steps_data
        }
    
    def get_sleep_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get sleep analytics for user."""
        end_date = date.today()
        start_date = date.fromordinal(end_date.toordinal() - days + 1)
        
        dates = self.list_metric_dates(user_id, 'sleep', start_date, end_date)
        
        if not dates:
            return {'error': 'No sleep data available'}
        
        sleep_data = []
        for date_str in dates:
            data = self.get_metric_data(user_id, 'sleep', date_str)
            if data and data.sleep_time_seconds > 0:
                total_time = data.sleep_time_seconds
                sleep_data.append({
                    'date': date_str,
                    'duration_hours': total_time / 3600,
                    'deep_sleep_hours': data.deep_sleep_seconds / 3600,
                    'light_sleep_hours': data.light_sleep_seconds / 3600,
                    'rem_sleep_hours': data.rem_sleep_seconds / 3600,
                    'awake_hours': data.awake_sleep_seconds / 3600,
                    'efficiency': getattr(data, 'sleep_efficiency_percentage', 0),
                    'awakenings': data.awake_count,
                    'avg_spo2': data.average_sp_o2_value,
                    'avg_respiration': data.average_respiration_value
                })
        
        if not sleep_data:
            return {'error': 'No valid sleep data found'}
        
        # Calculate analytics
        avg_duration = sum(d['duration_hours'] for d in sleep_data) / len(sleep_data)
        avg_deep = sum(d['deep_sleep_hours'] for d in sleep_data) / len(sleep_data)
        avg_rem = sum(d['rem_sleep_hours'] for d in sleep_data) / len(sleep_data)
        avg_efficiency = sum(d['efficiency'] for d in sleep_data if d['efficiency']) / len([d for d in sleep_data if d['efficiency']])
        
        # Sleep quality categories
        excellent_nights = sum(1 for d in sleep_data if d['duration_hours'] >= 7.5 and d['efficiency'] >= 85)
        good_nights = sum(1 for d in sleep_data if d['duration_hours'] >= 6.5 and d['efficiency'] >= 75)
        poor_nights = len(sleep_data) - good_nights
        
        return {
            'period': {'start': dates[0], 'end': dates[-1], 'days': len(dates)},
            'averages': {
                'duration_hours': round(avg_duration, 1),
                'deep_sleep_hours': round(avg_deep, 1),
                'rem_sleep_hours': round(avg_rem, 1),
                'efficiency_percentage': round(avg_efficiency, 1) if avg_efficiency else 0
            },
            'sleep_quality': {
                'excellent_nights': excellent_nights,
                'good_nights': good_nights,
                'poor_nights': poor_nights
            },
            'physiological': {
                'avg_spo2': round(sum(d['avg_spo2'] for d in sleep_data if d['avg_spo2']) / len([d for d in sleep_data if d['avg_spo2']]), 1) if any(d['avg_spo2'] for d in sleep_data) else None,
                'avg_respiration': round(sum(d['avg_respiration'] for d in sleep_data if d['avg_respiration']) / len([d for d in sleep_data if d['avg_respiration']]), 1) if any(d['avg_respiration'] for d in sleep_data) else None
            },
            'raw_data': sleep_data
        }
    
    def get_heart_rate_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get heart rate analytics for user."""
        end_date = date.today()
        start_date = date.fromordinal(end_date.toordinal() - days + 1)
        
        dates = self.list_metric_dates(user_id, 'heart_rate', start_date, end_date)
        
        if not dates:
            return {'error': 'No heart rate data available'}
        
        hr_data = []
        for date_str in dates:
            data = self.get_metric_data(user_id, 'heart_rate', date_str)
            if data and data.resting_heart_rate:
                hr_data.append({
                    'date': date_str,
                    'resting_hr': data.resting_heart_rate,
                    'max_hr': data.max_heart_rate,
                    'min_hr': data.min_heart_rate,
                    'avg_hr': getattr(data, 'avg_heart_rate', 0),
                    'hr_range': data.heart_rate_range if hasattr(data, 'heart_rate_range') else data.max_heart_rate - data.min_heart_rate
                })
        
        if not hr_data:
            return {'error': 'No valid heart rate data found'}
        
        # Calculate analytics
        avg_resting = sum(d['resting_hr'] for d in hr_data) / len(hr_data)
        avg_max = sum(d['max_hr'] for d in hr_data) / len(hr_data)
        
        # HRV trends (simplified)
        resting_trend = 'stable'
        if len(hr_data) >= 7:
            recent_avg = sum(d['resting_hr'] for d in hr_data[-7:]) / 7
            older_avg = sum(d['resting_hr'] for d in hr_data[:-7]) / len(hr_data[:-7])
            if recent_avg < older_avg - 2:
                resting_trend = 'improving'
            elif recent_avg > older_avg + 2:
                resting_trend = 'declining'
        
        return {
            'period': {'start': dates[0], 'end': dates[-1], 'days': len(dates)},
            'averages': {
                'resting_hr': round(avg_resting, 1),
                'max_hr': round(avg_max, 1)
            },
            'trends': {
                'resting_hr_trend': resting_trend
            },
            'raw_data': hr_data
        }
    
    # Sync operations
    def _get_api_client(self, user_id: str) -> APIClient:
        """Get API client for user."""
        if user_id not in self._api_clients:
            user = self.get_user(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            auth_client = AuthClient()
            # Load tokens if path is specified
            if user.get('auth_token_path'):
                # AuthClient will handle token loading
                pass
            
            self._api_clients[user_id] = APIClient(auth_client=auth_client)
        
        return self._api_clients[user_id]
    
    def _get_sync_manager(self, user_id: str) -> SyncManager:
        """Get sync manager for user."""
        if user_id not in self._sync_managers:
            api_client = self._get_api_client(user_id)
            self._sync_managers[user_id] = SyncManager(api_client, self.storage, user_id)
        
        return self._sync_managers[user_id]
    
    async def sync_user_data(self, user_id: str, start_date: date, end_date: date, progress_callback=None) -> Dict[str, Any]:
        """Sync ALL available metrics for user and date range."""
        sync_manager = self._get_sync_manager(user_id)
        return await sync_manager.sync_with_activities(start_date, end_date, progress_callback)
    
    async def sync_recent_user_data(self, user_id: str, days: int = 30, progress_callback=None) -> Dict[str, Any]:
        """Sync recent data (last N days) for ALL available metrics."""
        sync_manager = self._get_sync_manager(user_id)
        return await sync_manager.sync_recent_data(days, progress_callback)
    
    def get_sync_efficiency_stats(self, user_id: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get sync efficiency statistics for user."""
        sync_manager = self._get_sync_manager(user_id)
        return sync_manager.get_sync_efficiency_stats(start_date, end_date)
    
    # Database operations
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return self.storage.get_database_stats()
    
    def get_metric_stats(self, user_id: str, metric_type: str) -> Dict[str, Any]:
        """Get statistics for a specific metric."""
        return self.storage.get_metric_stats(user_id, metric_type)
    
    # Activities operations
    def get_activities_for_date_range(self, user_id: str, start_date: date, end_date: date):
        """Get activities for date range."""
        return self.storage.get_activities_for_date_range(user_id, start_date, end_date)
    
    def get_activities_count(self, user_id: str) -> int:
        """Get total activities count for user."""
        return self.storage.get_activities_count(user_id)