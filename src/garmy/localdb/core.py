"""Compact enhanced LocalDB with normalized storage - all in one file."""

import asyncio
import logging
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable

from sqlalchemy import Column, Date, DateTime, String, Integer, Float, Text, Boolean, create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from garmy.auth.client import AuthClient
from garmy.core.client import APIClient
from garmy.core.discovery import MetricDiscovery
from garmy.core.registry import MetricRegistry

logger = logging.getLogger(__name__)
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    user_id = Column(String(50), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_sync = Column(DateTime, nullable=True)


def create_table_for_metric(metric_name: str, config: Any) -> type:
    """Create normalized table for metric based on its type."""
    
    # Base columns for all metrics
    attrs = {
        '__tablename__': f"{metric_name}_data",
        'id': Column(Integer, primary_key=True, autoincrement=True),
        'user_id': Column(String(50), nullable=False),
        'data_date': Column(Date, nullable=False),
        'created_at': Column(DateTime, default=datetime.utcnow),
    }
    
    # Metric-specific columns based on known patterns
    if metric_name == 'activities':
        attrs.update({
            'activity_id': Column(String(50)),
            'activity_name': Column(String(255)),
            'sport_type': Column(String(100)),
            'duration': Column(Integer),
            'distance': Column(Float),
            'calories': Column(Integer),
        })
    elif metric_name == 'sleep':
        attrs.update({
            'sleep_time_seconds': Column(Integer),
            'deep_sleep_seconds': Column(Integer),
            'light_sleep_seconds': Column(Integer),
            'rem_sleep_seconds': Column(Integer),
            'awake_sleep_seconds': Column(Integer),
            'sleep_start_timestamp_gmt': Column(DateTime),
            'sleep_end_timestamp_gmt': Column(DateTime),
        })
    elif metric_name in ['heart_rate', 'body_battery', 'stress', 'respiration']:
        attrs.update({
            'min_value': Column(Integer),
            'max_value': Column(Integer),
            'avg_value': Column(Integer),
            'resting_value': Column(Integer),
            'values_json': Column(Text),  # For intraday data
        })
    elif metric_name == 'steps':
        attrs.update({
            'total_steps': Column(Integer),
            'step_goal': Column(Integer),
            'total_distance': Column(Integer),
            'daily_average': Column(Integer),
        })
    elif metric_name == 'hrv':
        attrs.update({
            'weekly_avg': Column(Integer),
            'last_night_avg': Column(Integer),
            'last_night_5_min_high': Column(Integer),
            'status': Column(String(50)),
            'feedback_phrase': Column(Text),
        })
    else:
        # Generic columns for other metrics
        attrs.update({
            'metric_value': Column(Float),
            'metric_data': Column(Text),  # JSON for complex data
        })
    
    return type(f"{metric_name.title()}Data", (Base,), attrs)


def extract_data_for_storage(metric_name: str, api_data: Any, target_date: str = None) -> Dict[str, Any]:
    """Extract data from API response for storage.
    
    Args:
        metric_name: Name of the metric
        api_data: API response data
        target_date: Target date in YYYY-MM-DD format for filtering
    """
    if not api_data:
        return {}
    
    data = {}
    
    try:
        if metric_name == 'activities':
            # Activities returns a list directly
            if api_data and isinstance(api_data, list) and len(api_data) > 0:
                activity = api_data[0]  # Take first activity
                data = {
                    'activity_id': getattr(activity, 'activity_id', None),
                    'activity_name': getattr(activity, 'activity_name', None),
                    'sport_type': getattr(activity, 'sport_type_key', None),
                    'duration': getattr(activity, 'duration', None),
                    'distance': getattr(activity, 'distance', None),
                    'calories': getattr(activity, 'calories', None),
                }
            else:
                data = {}
        elif metric_name == 'sleep':
            # Sleep data is in sleep_summary
            sleep_summary = getattr(api_data, 'sleep_summary', None) if api_data else None
            if sleep_summary:
                # Convert timestamps from milliseconds to datetime
                def convert_timestamp(ts):
                    if ts is not None:
                        return datetime.fromtimestamp(ts / 1000)
                    return None
                
                data = {
                    'sleep_time_seconds': getattr(sleep_summary, 'sleep_time_seconds', None),
                    'deep_sleep_seconds': getattr(sleep_summary, 'deep_sleep_seconds', None),
                    'light_sleep_seconds': getattr(sleep_summary, 'light_sleep_seconds', None),
                    'rem_sleep_seconds': getattr(sleep_summary, 'rem_sleep_seconds', None),
                    'awake_sleep_seconds': getattr(sleep_summary, 'awake_sleep_seconds', None),
                    'sleep_start_timestamp_gmt': convert_timestamp(getattr(sleep_summary, 'sleep_start_timestamp_gmt', None)),
                    'sleep_end_timestamp_gmt': convert_timestamp(getattr(sleep_summary, 'sleep_end_timestamp_gmt', None)),
                }
            else:
                data = {}
        elif metric_name in ['heart_rate', 'body_battery', 'stress', 'respiration']:
            # Extract summary data and store intraday as JSON
            import json
            
            def json_serializer(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, date):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            # Different extraction logic per metric type
            if metric_name == 'body_battery':
                # ИСПОЛЬЗУЕМ to_summary() для правильного извлечения Body Battery данных
                summary = api_data.to_summary() if hasattr(api_data, 'to_summary') else None
                if summary:
                    data = {
                        'min_value': summary.lowest_level,     # Минимальный уровень энергии за день
                        'max_value': summary.highest_level,    # Максимальный уровень энергии за день  
                        'avg_value': None,                     # API не предоставляет среднее для Body Battery
                        'resting_value': summary.start_level,  # Уровень в начале дня
                    }
                    # Store body battery values if present
                    if hasattr(api_data, 'body_battery_values_array') and api_data.body_battery_values_array:
                        data['values_json'] = json.dumps(api_data.body_battery_values_array, default=json_serializer)
                else:
                    data = {}
            elif metric_name == 'stress':
                data = {
                    'min_value': None,
                    'max_value': getattr(api_data, 'max_stress_level', None),
                    'avg_value': getattr(api_data, 'avg_stress_level', None),
                    'resting_value': None,
                }
                # Store stress values if present
                if hasattr(api_data, 'stress_values_array') and api_data.stress_values_array:
                    data['values_json'] = json.dumps(api_data.stress_values_array, default=json_serializer)
            elif metric_name == 'heart_rate':
                # Heart rate data is in heart_rate_summary
                hr_summary = getattr(api_data, 'heart_rate_summary', None) if api_data else None
                if hr_summary:
                    data = {
                        'min_value': getattr(hr_summary, 'min_heart_rate', None),
                        'max_value': getattr(hr_summary, 'max_heart_rate', None),
                        'avg_value': None,  # Not in summary
                        'resting_value': getattr(hr_summary, 'resting_heart_rate', None),
                    }
                    # Store intraday values as JSON if present
                    if hasattr(api_data, 'heart_rate_values_array') and api_data.heart_rate_values_array:
                        data['values_json'] = json.dumps(api_data.heart_rate_values_array, default=json_serializer)
                else:
                    data = {}
            elif metric_name == 'respiration':
                # Respiration data is in respiration_summary
                resp_summary = getattr(api_data, 'respiration_summary', None) if api_data else None
                if resp_summary:
                    # ИСПРАВЛЕНО: используем правильные названия полей из dataclass
                    data = {
                        'min_value': getattr(resp_summary, 'lowest_respiration_value', None),
                        'max_value': getattr(resp_summary, 'highest_respiration_value', None),
                        'avg_value': getattr(resp_summary, 'avg_waking_respiration_value', None),
                        'resting_value': getattr(resp_summary, 'avg_sleep_respiration_value', None),  # Используем сон как "покой"
                    }
                    # Store respiration values as JSON if present
                    if hasattr(api_data, 'respiration_values_array') and api_data.respiration_values_array:
                        data['values_json'] = json.dumps(api_data.respiration_values_array, default=json_serializer)
                else:
                    data = {}
        elif metric_name == 'steps':
            # Steps data has daily_steps (list) and aggregations structure
            daily_steps_list = getattr(api_data, 'daily_steps', None) if api_data else None
            if daily_steps_list and isinstance(daily_steps_list, list):
                # Find the correct date's data from the list
                target_steps = None
                if target_date:
                    # Look for exact date match
                    for daily_step in daily_steps_list:
                        if hasattr(daily_step, 'calendar_date') and daily_step.calendar_date == target_date:
                            target_steps = daily_step
                            break
                
                # If no exact match or no target_date, take the last item (most recent)
                if not target_steps and daily_steps_list:
                    target_steps = daily_steps_list[-1]
                
                if target_steps:
                    data = {
                        'total_steps': getattr(target_steps, 'total_steps', None),
                        'step_goal': getattr(target_steps, 'step_goal', None),
                        'total_distance': getattr(target_steps, 'total_distance', None),
                        'daily_average': getattr(api_data.aggregations, 'daily_average', None) if hasattr(api_data, 'aggregations') else None,
                    }
                else:
                    data = {}
            else:
                data = {}
        elif metric_name == 'hrv':
            # HRV data is in hrv_summary
            hrv_summary = getattr(api_data, 'hrv_summary', None) if api_data else None
            if hrv_summary:
                data = {
                    'weekly_avg': getattr(hrv_summary, 'weekly_avg', None),
                    'last_night_avg': getattr(hrv_summary, 'last_night_avg', None),
                    'last_night_5_min_high': getattr(hrv_summary, 'last_night_5_min_high', None),
                    'status': getattr(hrv_summary, 'status', None),
                    'feedback_phrase': getattr(hrv_summary, 'feedback_phrase', None),
                }
            else:
                data = {}
        else:
            # Generic handling - extract basic numeric value and store full data as JSON
            import json
            if hasattr(api_data, '__dict__'):
                # Convert datetime objects to strings for JSON serialization
                def json_serializer(obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    elif isinstance(obj, date):
                        return obj.isoformat()
                    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
                
                data = {
                    'metric_value': None,  # Extract main value if possible
                    'metric_data': json.dumps(api_data.__dict__, default=json_serializer),
                }
            else:
                data = {'metric_data': str(api_data)}
    
    except Exception as e:
        logger.error(f"Error extracting data for {metric_name}: {e}")
        return {}
    
    return data


class LocalDB:
    """Compact enhanced LocalDB with normalized storage."""
    
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup database
        self.engine = create_engine(f"sqlite:///{self.db_path}", connect_args={'check_same_thread': False})
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Discover metrics and create tables
        self.metric_configs = MetricDiscovery.discover_metrics()
        self.metric_tables = {}
        self._create_all_tables()
        
        # Initialize API client components
        self._auth_client = None
        self._api_client = None
    
    def _create_all_tables(self):
        """Create all tables for discovered metrics."""
        try:
            # Create user table
            Base.metadata.create_all(self.engine, tables=[User.__table__])
            
            # Create metric tables
            for metric_name, config in self.metric_configs.items():
                table_class = create_table_for_metric(metric_name, config)
                self.metric_tables[metric_name] = table_class
                
            # Create all metric tables
            Base.metadata.create_all(self.engine)
            
            logger.info(f"Created tables for {len(self.metric_tables)} metrics")
            
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
    
    @contextmanager
    def get_session(self) -> Session:
        """Get database session with proper cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def add_user(self, user_id: str, email: str) -> None:
        """Add user to database."""
        with self.get_session() as session:
            session.merge(User(user_id=user_id, email=email))
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from database."""
        with self.get_session() as session:
            user = session.query(User).filter_by(user_id=user_id).first()
            return {'user_id': user.user_id, 'email': user.email} if user else None
    
    def list_users(self) -> List[Dict[str, Any]]:
        """List all users."""
        with self.get_session() as session:
            return [{'user_id': u.user_id, 'email': u.email} for u in session.query(User).all()]
    
    def store_metric(self, user_id: str, metric_type: str, data_date: Union[str, date], api_data: Any) -> bool:
        """Store metric data in normalized table."""
        try:
            if metric_type not in self.metric_tables:
                logger.warning(f"No table for metric {metric_type}")
                return False
            
            # Convert date
            if isinstance(data_date, str):
                data_date = datetime.strptime(data_date, "%Y-%m-%d").date()
            
            # Extract data for storage
            target_date_str = data_date.strftime("%Y-%m-%d")
            extracted_data = extract_data_for_storage(metric_type, api_data, target_date_str)
            if not extracted_data:
                logger.debug(f"No data to store for {metric_type}")
                return True  # Not an error, just no data
            
            # Add base fields
            extracted_data.update({
                'user_id': user_id,
                'data_date': data_date,
            })
            
            # Store in database
            table_class = self.metric_tables[metric_type]
            with self.get_session() as session:
                # Delete existing record for this user/date/metric
                session.query(table_class).filter_by(
                    user_id=user_id,
                    data_date=data_date
                ).delete()
                
                # Insert new record
                record = table_class(**extracted_data)
                session.add(record)
            
            logger.debug(f"Stored {metric_type} data for {user_id} on {data_date}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing {metric_type} data: {e}")
            return False
    
    def get_metric(self, user_id: str, metric_type: str, data_date: Union[str, date]) -> Optional[Any]:
        """Retrieve metric data from normalized table."""
        try:
            if metric_type not in self.metric_tables:
                return None
            
            if isinstance(data_date, str):
                data_date = datetime.strptime(data_date, "%Y-%m-%d").date()
            
            table_class = self.metric_tables[metric_type]
            with self.get_session() as session:
                record = session.query(table_class).filter_by(
                    user_id=user_id,
                    data_date=data_date
                ).first()
                
                if record:
                    # Convert back to dict
                    return {c.name: getattr(record, c.name) for c in record.__table__.columns}
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving {metric_type} data: {e}")
            return None
    
    def has_metric(self, user_id: str, metric_type: str, data_date: Union[str, date]) -> bool:
        """Check if metric data already exists."""
        try:
            if metric_type not in self.metric_tables:
                return False
            
            if isinstance(data_date, str):
                data_date = datetime.strptime(data_date, "%Y-%m-%d").date()
            
            table_class = self.metric_tables[metric_type]
            with self.get_session() as session:
                count = session.query(table_class).filter_by(
                    user_id=user_id,
                    data_date=data_date
                ).count()
                
                return count > 0
                
        except Exception as e:
            logger.error(f"Error checking {metric_type} existence: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self.get_session() as session:
                stats = {
                    'total_metrics': len(self.metric_tables),
                    'users': session.query(User).count(),
                    'metrics': {}
                }
                
                total_records = 0
                for metric_name, table_class in self.metric_tables.items():
                    count = session.query(table_class).count()
                    stats['metrics'][metric_name] = count
                    total_records += count
                
                stats['total_records'] = total_records
                return stats
                
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}
    
    def _get_api_client(self) -> APIClient:
        """Get API client instance."""
        if not self._api_client:
            if not self._auth_client:
                self._auth_client = AuthClient()
            self._api_client = APIClient(auth_client=self._auth_client)
        
        return self._api_client
    
    async def sync_user_data(self, user_id: str, start_date: date, end_date: date, 
                            progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Sync user data for date range."""
        try:
            api_client = self._get_api_client()
            
            # Get available metrics
            available_metrics = list(self.metric_tables.keys())
            logger.info(f"Syncing {len(available_metrics)} metrics")
            
            # Build date range (reverse chronological)
            date_range = []
            current = end_date
            while current >= start_date:
                date_range.append(current)
                current -= timedelta(days=1)
            
            results = {
                'metrics_synced': {m: {'success': 0, 'failed': 0, 'skipped': 0} for m in available_metrics},
                'total_success': 0,
                'total_failed': 0,
                'total_skipped': 0,
                'errors': []
            }
            
            total_items = len(date_range) * len(available_metrics)
            completed_items = 0
            
            for date_idx, sync_date in enumerate(date_range):
                for metric_idx, metric_type in enumerate(available_metrics):
                    completed_items = date_idx * len(available_metrics) + metric_idx
                    
                    if progress_callback:
                        progress_callback({
                            'current_date': sync_date.isoformat(),
                            'current_metric': metric_type,
                            'completed_items': completed_items,
                            'total_items': total_items,
                        })
                    
                    try:
                        # Check if data already exists (skip mechanism)
                        if self.has_metric(user_id, metric_type, sync_date):
                            results['metrics_synced'][metric_type]['skipped'] += 1
                            results['total_skipped'] += 1
                            logger.debug(f"⏭ {metric_type} skipped for {sync_date} (already exists)")
                            continue
                        
                        # Get data from API
                        accessor = api_client.metrics.get(metric_type)
                        if not accessor:
                            results['metrics_synced'][metric_type]['failed'] += 1
                            results['total_failed'] += 1
                            continue
                        
                        data = accessor.get(sync_date.isoformat())
                        if not data:
                            logger.debug(f"No data for {metric_type} on {sync_date}")
                            results['metrics_synced'][metric_type]['failed'] += 1
                            results['total_failed'] += 1
                            continue
                        
                        # Store data
                        success = self.store_metric(user_id, metric_type, sync_date, data)
                        if success:
                            results['metrics_synced'][metric_type]['success'] += 1
                            results['total_success'] += 1
                            logger.debug(f"✓ {metric_type} synced for {sync_date}")
                        else:
                            results['metrics_synced'][metric_type]['failed'] += 1
                            results['total_failed'] += 1
                            logger.debug(f"✗ {metric_type} failed for {sync_date}")
                    
                    except Exception as e:
                        error_msg = f"Error syncing {metric_type} for {sync_date}: {e}"
                        results['errors'].append(error_msg)
                        results['metrics_synced'][metric_type]['failed'] += 1
                        results['total_failed'] += 1
                        logger.error(error_msg)
                
                # Small delay between dates
                await asyncio.sleep(0.1)
            
            logger.info(f"Sync completed: {results['total_success']} success, {results['total_failed']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Sync error: {e}")
            return {'error': str(e), 'total_success': 0, 'total_failed': 0}


# Legacy compatibility wrapper
class LocalDBClient:
    """Wrapper for enhanced LocalDB with legacy interface."""
    
    def __init__(self, db_path: Union[str, Path], use_enhanced_storage: bool = True):
        self.enhanced_db = LocalDB(db_path)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def add_user(self, user_id: str, email: str) -> None:
        return self.enhanced_db.add_user(user_id, email)
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.enhanced_db.get_user(user_id)
    
    def list_users(self) -> List[Dict[str, Any]]:
        return self.enhanced_db.list_users()
    
    def get_database_stats(self) -> Dict[str, Any]:
        return self.enhanced_db.get_stats()
    
    async def sync_user_data(self, user_id: str, start_date: date, end_date: date, 
                            progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        return await self.enhanced_db.sync_user_data(user_id, start_date, end_date, progress_callback)
    
    def get_metric_data(self, user_id: str, metric_type: str, data_date: Union[str, date]) -> Optional[Any]:
        return self.enhanced_db.get_metric(user_id, metric_type, data_date)