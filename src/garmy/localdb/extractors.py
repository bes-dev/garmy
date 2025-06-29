"""Data extraction utilities for converting API responses to database format."""

from datetime import date
from typing import Any, Dict, List, Optional, Tuple
from .models import MetricType


class DataExtractor:
    """Extracts and normalizes data from API responses for database storage."""
    
    def extract_metric_data(self, data: Any, metric_type: MetricType) -> Optional[Dict]:
        """Extract data based on metric type."""
        if metric_type == MetricType.DAILY_SUMMARY:
            return self._extract_daily_summary_data(data)
        elif metric_type == MetricType.SLEEP:
            return self._extract_sleep_data(data)
        elif metric_type == MetricType.TRAINING_READINESS:
            return self._extract_training_readiness_data(data)
        elif metric_type == MetricType.HRV:
            return self._extract_hrv_data(data)
        elif metric_type == MetricType.RESPIRATION:
            return self._extract_respiration_summary(data)
        elif metric_type == MetricType.ACTIVITIES:
            return self._extract_activity_data(data)
        else:
            return None
    
    def _extract_daily_summary_data(self, data: Any) -> Dict[str, Any]:
        """Extract daily summary data."""
        return {
            'total_steps': getattr(data, 'total_steps', None),
            'step_goal': getattr(data, 'step_goal', None),
            'total_distance_meters': getattr(data, 'total_distance_meters', None),
            'total_calories': getattr(data, 'total_kilocalories', None),
            'active_calories': getattr(data, 'active_kilocalories', None),
            'bmr_calories': getattr(data, 'bmr_kilocalories', None),
            'resting_heart_rate': getattr(data, 'resting_heart_rate', None),
            'max_heart_rate': getattr(data, 'max_heart_rate', None),
            'min_heart_rate': getattr(data, 'min_heart_rate', None),
            'average_heart_rate': getattr(data, 'average_heart_rate', None),
            'avg_stress_level': getattr(data, 'avg_stress_level', None),
            'max_stress_level': getattr(data, 'max_stress_level', None),
            'body_battery_high': getattr(data, 'body_battery_highest_value', None),
            'body_battery_low': getattr(data, 'body_battery_lowest_value', None)
        }
    
    def _extract_sleep_data(self, data: Any) -> Dict[str, Any]:
        """Extract sleep data with percentages and durations."""
        sleep_data = {
            'sleep_duration_hours': getattr(data, 'sleep_time_seconds', 0) / 3600 if getattr(data, 'sleep_time_seconds', None) else None,
            'deep_sleep_percentage': getattr(data, 'deep_sleep_seconds', 0) / getattr(data, 'sleep_time_seconds', 1) * 100 if getattr(data, 'sleep_time_seconds', None) and getattr(data, 'deep_sleep_seconds', None) else None,
            'light_sleep_percentage': getattr(data, 'light_sleep_seconds', 0) / getattr(data, 'sleep_time_seconds', 1) * 100 if getattr(data, 'sleep_time_seconds', None) and getattr(data, 'light_sleep_seconds', None) else None,
            'rem_sleep_percentage': getattr(data, 'rem_sleep_seconds', 0) / getattr(data, 'sleep_time_seconds', 1) * 100 if getattr(data, 'sleep_time_seconds', None) and getattr(data, 'rem_sleep_seconds', None) else None,
            'awake_percentage': getattr(data, 'awake_seconds', 0) / getattr(data, 'sleep_time_seconds', 1) * 100 if getattr(data, 'sleep_time_seconds', None) and getattr(data, 'awake_seconds', None) else None,
            'average_spo2': getattr(data, 'average_sp_o2_value', None),
            'average_respiration': getattr(data, 'average_respiration_value', None)
        }
        return sleep_data
    
    def _extract_heart_rate_summary(self, data: Any) -> Dict[str, Any]:
        """Extract heart rate summary data."""
        return {
            'resting_heart_rate': getattr(data, 'resting_heart_rate', None),
            'max_heart_rate': getattr(data, 'max_heart_rate', None),
            'min_heart_rate': getattr(data, 'min_heart_rate', None)
        }
    
    def _extract_training_readiness_data(self, data: Any) -> Dict[str, Any]:
        """Extract training readiness nested data."""
        return {
            'score': getattr(data, 'score', None),
            'level': getattr(data, 'level', None),
            'feedback': getattr(data, 'feedback_short', None)
        }
    
    def _extract_hrv_data(self, data: Any) -> Dict[str, Any]:
        """Extract HRV using nested summary."""
        hrv_summary = getattr(data, 'hrv_summary', None)
        if hrv_summary:
            return {
                'weekly_avg': getattr(hrv_summary, 'weekly_avg', None),
                'last_night_avg': getattr(hrv_summary, 'last_night_avg', None),
                'status': getattr(hrv_summary, 'status', None)
            }
        return {}
    
    def _extract_respiration_summary(self, data: Any) -> Dict[str, Any]:
        """Extract respiration summary - unique respiratory metrics."""
        summary = getattr(data, 'respiration_summary', None)
        if summary:
            return {
                'avg_waking_respiration_value': getattr(summary, 'avg_waking_respiration_value', None),
                'avg_sleep_respiration_value': getattr(summary, 'avg_sleep_respiration_value', None),
                'lowest_respiration_value': getattr(summary, 'lowest_respiration_value', None),
                'highest_respiration_value': getattr(summary, 'highest_respiration_value', None)
            }
        return {}
    
    def _extract_activity_data(self, data: Any) -> Dict[str, Any]:
        """Extract activity data from both parsed and raw formats."""
        # Handle both object attributes and dict keys
        def get_value(obj, *keys):
            for key in keys:
                if hasattr(obj, key):
                    return getattr(obj, key, None)
                elif isinstance(obj, dict) and key in obj:
                    return obj[key]
            return None
        
        activity_id = get_value(data, 'activity_id', 'activityId')
        if activity_id:
            return {
                'activity_id': activity_id,
                'activity_name': get_value(data, 'activity_name', 'activityName', 'activityTypeName'),
                'duration_seconds': get_value(data, 'duration', 'movingDuration', 'elapsedDuration'),
                'avg_heart_rate': get_value(data, 'average_hr', 'averageHR', 'avgHR'),
                'training_load': get_value(data, 'activity_training_load', 'trainingLoad'),
                'start_time': get_value(data, 'start_time_local', 'startTimeLocal', 'start_time')
            }
        return {}
    
    def extract_timeseries_data(self, data: Any, metric_type: MetricType) -> List[Tuple]:
        """Extract timeseries data points."""
        if not hasattr(data, 'data_points') or not data.data_points:
            return []
        
        timeseries_data = []
        for point in data.data_points:
            if hasattr(point, 'timestamp') and hasattr(point, 'value'):
                timestamp = point.timestamp
                value = point.value
                metadata = {}
                
                # Add metric-specific metadata
                if metric_type == MetricType.HEART_RATE and hasattr(point, 'zone'):
                    metadata['zone'] = point.zone
                elif metric_type == MetricType.STRESS and hasattr(point, 'stress_level'):
                    metadata['stress_level'] = point.stress_level
                
                timeseries_data.append((timestamp, value, metadata))
        
        return timeseries_data