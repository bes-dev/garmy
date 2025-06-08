"""Refactored LocalDB with clean architecture and separation of concerns."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Protocol

from sqlalchemy import Column, Date, DateTime, String, Integer, Float, Text, create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from garmy.auth.client import AuthClient
from garmy.core.client import APIClient
from garmy.core.discovery import MetricDiscovery
from .exceptions import DatabaseError, SyncError, ValidationError

logger = logging.getLogger(__name__)

# Global base for shared tables like User
GlobalBase = declarative_base()


@dataclass
class SyncResult:
    total_success: int = 0
    total_failed: int = 0
    total_skipped: int = 0
    metrics_synced: Dict[str, Dict[str, int]] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.metrics_synced is None:
            self.metrics_synced = {}
        if self.errors is None:
            self.errors = []


class User(GlobalBase):
    __tablename__ = 'users'
    user_id = Column(String(50), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_sync = Column(DateTime, nullable=True)


class MetricExtractor(ABC):
    """Abstract base for metric data extractors."""
    
    @abstractmethod
    def extract(self, api_data: Any, target_date: str = None) -> Dict[str, Any]:
        """Extract data from API response for storage."""
        pass


class ActivityExtractor(MetricExtractor):
    def extract(self, api_data: Any, target_date: str = None) -> Dict[str, Any]:
        # Activities API returns a list of ActivitySummary instances
        if not api_data or not isinstance(api_data, list) or len(api_data) == 0:
            return {}
        
        # For activities, we store as JSON to preserve all data
        # Activities are complex with many optional fields and nested data
        activities_data = []
        
        for activity in api_data:
            # Convert ActivitySummary dataclass to dict for JSON storage
            if hasattr(activity, '__dataclass_fields__'):
                activity_dict = {}
                for field_name in activity.__dataclass_fields__:
                    value = getattr(activity, field_name, None)
                    # Handle nested dicts and convert datetime objects
                    if hasattr(value, 'isoformat'):  # datetime objects
                        activity_dict[field_name] = value.isoformat()
                    else:
                        activity_dict[field_name] = value
                activities_data.append(activity_dict)
            else:
                # Fallback for unexpected data structure
                activities_data.append(str(activity))
        
        return {
            'activities_json': json.dumps(activities_data, default=self._json_serializer),
            'activity_count': len(activities_data),
            'latest_activity_date': self._get_latest_activity_date(api_data) if activities_data else None,
        }
    
    def _get_latest_activity_date(self, api_data):
        """Extract the latest activity date from the activities list."""
        if not api_data or not isinstance(api_data, list):
            return None
        
        latest_date = None
        for activity in api_data:
            activity_date = getattr(activity, 'activity_date', None)
            if activity_date:
                if isinstance(activity_date, str):
                    if latest_date is None or activity_date > latest_date:
                        latest_date = activity_date
                elif hasattr(activity_date, 'isoformat'):
                    date_str = activity_date.isoformat()
                    if latest_date is None or date_str > latest_date:
                        latest_date = date_str
        
        return latest_date
    
    def _json_serializer(self, obj):
        """JSON serializer for non-standard types."""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class SleepExtractor(MetricExtractor):
    def extract(self, api_data: Any, target_date: str = None) -> Dict[str, Any]:
        sleep_summary = getattr(api_data, 'sleep_summary', None) if api_data else None
        if not sleep_summary:
            return {}
        
        def convert_timestamp(ts):
            return datetime.fromtimestamp(ts / 1000) if ts is not None else None
        
        return {
            'sleep_time_seconds': getattr(sleep_summary, 'sleep_time_seconds', None),
            'deep_sleep_seconds': getattr(sleep_summary, 'deep_sleep_seconds', None),
            'light_sleep_seconds': getattr(sleep_summary, 'light_sleep_seconds', None),
            'rem_sleep_seconds': getattr(sleep_summary, 'rem_sleep_seconds', None),
            'awake_sleep_seconds': getattr(sleep_summary, 'awake_sleep_seconds', None),
            'sleep_start_timestamp_gmt': convert_timestamp(getattr(sleep_summary, 'sleep_start_timestamp_gmt', None)),
            'sleep_end_timestamp_gmt': convert_timestamp(getattr(sleep_summary, 'sleep_end_timestamp_gmt', None)),
        }


class BodyBatteryExtractor(MetricExtractor):
    def extract(self, api_data: Any, target_date: str = None) -> Dict[str, Any]:
        summary = api_data.to_summary() if hasattr(api_data, 'to_summary') else None
        if not summary:
            return {}
        
        data = {
            'min_value': summary.lowest_level,
            'max_value': summary.highest_level,
            'avg_value': None,
            'resting_value': summary.start_level,
        }
        
        if hasattr(api_data, 'body_battery_values_array') and api_data.body_battery_values_array:
            data['values_json'] = json.dumps(api_data.body_battery_values_array, default=self._json_serializer)
        
        return data
    
    def _json_serializer(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class GenericSummaryExtractor(MetricExtractor):
    """Generic extractor for heart_rate, stress, respiration."""
    
    def __init__(self, summary_attr: str, field_mapping: Dict[str, str]):
        self.summary_attr = summary_attr
        self.field_mapping = field_mapping
    
    def extract(self, api_data: Any, target_date: str = None) -> Dict[str, Any]:
        summary = getattr(api_data, self.summary_attr, None) if api_data else None
        if not summary:
            return {}
        
        result = {}
        for key, field in self.field_mapping.items():
            if field is not None:
                result[key] = getattr(summary, field, None)
            else:
                result[key] = None
        return result


class StepsExtractor(MetricExtractor):
    def extract(self, api_data: Any, target_date: str = None) -> Dict[str, Any]:
        daily_steps_list = getattr(api_data, 'daily_steps', None) if api_data else None
        if not daily_steps_list or not isinstance(daily_steps_list, list):
            return {}
        
        # Find the correct date's data from the list
        target_steps = None
        if target_date:
            for daily_step in daily_steps_list:
                if hasattr(daily_step, 'calendar_date') and daily_step.calendar_date == target_date:
                    target_steps = daily_step
                    break
        
        # If no exact match or no target_date, take the last item (most recent)
        if not target_steps and daily_steps_list:
            target_steps = daily_steps_list[-1]
        
        if not target_steps:
            return {}
        
        return {
            'total_steps': getattr(target_steps, 'total_steps', None),
            'step_goal': getattr(target_steps, 'step_goal', None),
            'total_distance': getattr(target_steps, 'total_distance', None),
            'daily_average': getattr(api_data.aggregations, 'daily_average', None) if hasattr(api_data, 'aggregations') else None,
        }


class HRVExtractor(MetricExtractor):
    def extract(self, api_data: Any, target_date: str = None) -> Dict[str, Any]:
        hrv_summary = getattr(api_data, 'hrv_summary', None) if api_data else None
        if not hrv_summary:
            return {}
        
        return {
            'weekly_avg': getattr(hrv_summary, 'weekly_avg', None),
            'last_night_avg': getattr(hrv_summary, 'last_night_avg', None),
            'last_night_5_min_high': getattr(hrv_summary, 'last_night_5_min_high', None),
            'status': getattr(hrv_summary, 'status', None),
            'feedback_phrase': getattr(hrv_summary, 'feedback_phrase', None),
        }


class MetricExtractorFactory:
    """Factory for creating metric extractors."""
    
    _extractors = {
        'activities': ActivityExtractor(),
        'sleep': SleepExtractor(),
        'body_battery': BodyBatteryExtractor(),
        'steps': StepsExtractor(),
        'hrv': HRVExtractor(),
        'heart_rate': GenericSummaryExtractor('heart_rate_summary', {
            'min_value': 'min_heart_rate',
            'max_value': 'max_heart_rate',
            'avg_value': None,
            'resting_value': 'resting_heart_rate'
        }),
        'respiration': GenericSummaryExtractor('respiration_summary', {
            'min_value': 'lowest_respiration_value',
            'max_value': 'highest_respiration_value',
            'avg_value': 'avg_waking_respiration_value',
            'resting_value': 'avg_sleep_respiration_value'
        }),
        'stress': GenericSummaryExtractor('stress_summary', {
            'min_value': 'min_stress_level',
            'max_value': 'max_stress_level',
            'avg_value': 'average_stress_level',
            'resting_value': 'rest_stress_level'
        }),
    }
    
    @classmethod
    def get_extractor(cls, metric_name: str) -> Optional[MetricExtractor]:
        return cls._extractors.get(metric_name)


class TableSchemaBuilder:
    """Builds table schemas for different metric types."""
    
    def __init__(self, metadata: MetaData):
        self.metadata = metadata
        self.base = declarative_base(metadata=metadata)
    
    def create_table_for_metric(self, metric_name: str, config: Any) -> type:
        base_attrs = {
            '__tablename__': f"{metric_name}_data",
            'id': Column(Integer, primary_key=True, autoincrement=True),
            'user_id': Column(String(50), nullable=False),
            'data_date': Column(Date, nullable=False),
            'created_at': Column(DateTime, default=datetime.utcnow),
        }
        
        schemas = {
            'activities': {
                'activities_json': Column(Text),  # JSON array of all activities
                'activity_count': Column(Integer),  # Number of activities stored
                'latest_activity_date': Column(String(20)),  # Date of most recent activity
            },
            'sleep': {
                'sleep_time_seconds': Column(Integer),
                'deep_sleep_seconds': Column(Integer),
                'light_sleep_seconds': Column(Integer),
                'rem_sleep_seconds': Column(Integer),
                'awake_sleep_seconds': Column(Integer),
                'sleep_start_timestamp_gmt': Column(DateTime),
                'sleep_end_timestamp_gmt': Column(DateTime),
            },
            'hrv': {
                'weekly_avg': Column(Integer),
                'last_night_avg': Column(Integer),
                'last_night_5_min_high': Column(Integer),
                'status': Column(String(50)),
                'feedback_phrase': Column(Text),
            },
            'steps': {
                'total_steps': Column(Integer),
                'step_goal': Column(Integer),
                'total_distance': Column(Integer),
                'daily_average': Column(Integer),
            }
        }
        
        summary_metrics = ['heart_rate', 'body_battery', 'stress', 'respiration']
        if metric_name in summary_metrics:
            schema = {
                'min_value': Column(Integer),
                'max_value': Column(Integer),
                'avg_value': Column(Integer),
                'resting_value': Column(Integer),
                'values_json': Column(Text),
            }
        else:
            schema = schemas.get(metric_name, {
                'metric_value': Column(Float),
                'metric_data': Column(Text),
            })
        
        base_attrs.update(schema)
        return type(f"{metric_name.title()}Data", (self.base,), base_attrs)


class DataProcessor:
    """Handles data extraction and processing for metrics."""
    
    def __init__(self):
        self.extractor_factory = MetricExtractorFactory()
    
    def extract_data_for_storage(self, metric_name: str, api_data: Any, target_date: str = None) -> Dict[str, Any]:
        """Extract data from API response for storage."""
        if not api_data:
            return {}
        
        try:
            extractor = self.extractor_factory.get_extractor(metric_name)
            if extractor:
                return extractor.extract(api_data, target_date)
            
            # Fallback for unsupported metrics
            return self._extract_generic(api_data)
            
        except Exception as e:
            logger.error(f"Error extracting data for {metric_name}: {e}")
            return {}
    
    def _extract_generic(self, api_data: Any) -> Dict[str, Any]:
        """Generic extraction for unsupported metrics."""
        if hasattr(api_data, '__dict__'):
            return {
                'metric_value': None,
                'metric_data': json.dumps(api_data.__dict__, default=self._json_serializer),
            }
        return {'metric_data': str(api_data)}
    
    def _json_serializer(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class DatabaseManager:
    """Manages database connections and session lifecycle."""
    
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.db_path}", connect_args={'check_same_thread': False})
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.metadata = MetaData()
    
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
    
    def create_tables(self, metric_tables: Dict[str, type]):
        """Create all tables in the database."""
        try:
            # Create the User table with its own metadata
            GlobalBase.metadata.create_all(self.engine, tables=[User.__table__])
            # Create metric tables with their own metadata
            self.metadata.create_all(self.engine)
            logger.info(f"Created tables for {len(metric_tables)} metrics")
        except Exception as e:
            raise DatabaseError(f"Failed to create tables: {e}")


class MetricRepository:
    """Repository for metric data operations."""
    
    def __init__(self, db_manager: DatabaseManager, data_processor: DataProcessor):
        self.db_manager = db_manager
        self.data_processor = data_processor
        self.metric_tables = {}
    
    def initialize_tables(self):
        """Initialize metric tables from discovered metrics."""
        metric_configs = MetricDiscovery.discover_metrics()
        schema_builder = TableSchemaBuilder(self.db_manager.metadata)
        
        for metric_name, config in metric_configs.items():
            table_class = schema_builder.create_table_for_metric(metric_name, config)
            self.metric_tables[metric_name] = table_class
            
        self.db_manager.create_tables(self.metric_tables)
    
    def store_metric(self, user_id: str, metric_type: str, data_date: Union[str, date], api_data: Any) -> bool:
        """Store metric data in normalized table."""
        if metric_type not in self.metric_tables:
            logger.warning(f"No table for metric {metric_type}")
            return False
        
        try:
            # Convert date and extract data
            if isinstance(data_date, str):
                data_date = datetime.strptime(data_date, "%Y-%m-%d").date()
            
            target_date_str = data_date.strftime("%Y-%m-%d")
            extracted_data = self.data_processor.extract_data_for_storage(metric_type, api_data, target_date_str)
            
            if not extracted_data:
                logger.debug(f"No data to store for {metric_type}")
                return True
            
            # Add base fields and store
            extracted_data.update({'user_id': user_id, 'data_date': data_date})
            
            table_class = self.metric_tables[metric_type]
            with self.db_manager.get_session() as session:
                session.query(table_class).filter_by(user_id=user_id, data_date=data_date).delete()
                session.add(table_class(**extracted_data))
            
            logger.debug(f"Stored {metric_type} data for {user_id} on {data_date}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing {metric_type} data: {e}")
            return False
    
    def get_metric(self, user_id: str, metric_type: str, data_date: Union[str, date]) -> Optional[Dict[str, Any]]:
        """Retrieve metric data from normalized table."""
        if metric_type not in self.metric_tables:
            return None
        
        try:
            if isinstance(data_date, str):
                data_date = datetime.strptime(data_date, "%Y-%m-%d").date()
            
            table_class = self.metric_tables[metric_type]
            with self.db_manager.get_session() as session:
                record = session.query(table_class).filter_by(user_id=user_id, data_date=data_date).first()
                return {c.name: getattr(record, c.name) for c in record.__table__.columns} if record else None
                
        except Exception as e:
            logger.error(f"Error retrieving {metric_type} data: {e}")
            return None
    
    def has_metric(self, user_id: str, metric_type: str, data_date: Union[str, date]) -> bool:
        """Check if metric data already exists."""
        if metric_type not in self.metric_tables:
            return False
        
        try:
            if isinstance(data_date, str):
                data_date = datetime.strptime(data_date, "%Y-%m-%d").date()
            
            table_class = self.metric_tables[metric_type]
            with self.db_manager.get_session() as session:
                return session.query(table_class).filter_by(user_id=user_id, data_date=data_date).count() > 0
                
        except Exception as e:
            logger.error(f"Error checking {metric_type} existence: {e}")
            return False


class UserRepository:
    """Repository for user data operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def add_user(self, user_id: str, email: str) -> None:
        """Add user to database."""
        with self.db_manager.get_session() as session:
            session.merge(User(user_id=user_id, email=email))
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from database."""
        with self.db_manager.get_session() as session:
            user = session.query(User).filter_by(user_id=user_id).first()
            return {'user_id': user.user_id, 'email': user.email} if user else None
    
    def list_users(self) -> List[Dict[str, Any]]:
        """List all users."""
        with self.db_manager.get_session() as session:
            return [{'user_id': u.user_id, 'email': u.email} for u in session.query(User).all()]


class SyncService:
    """Service for synchronizing data with Garmin API."""
    
    def __init__(self, metric_repository: MetricRepository):
        self.metric_repository = metric_repository
        self._auth_client = None
        self._api_client = None
    
    def _get_api_client(self) -> APIClient:
        """Get API client instance."""
        if not self._api_client:
            if not self._auth_client:
                self._auth_client = AuthClient()
            self._api_client = APIClient(auth_client=self._auth_client)
        return self._api_client
    
    async def sync_user_data(self, user_id: str, start_date: date, end_date: date, 
                            progress_callback: Optional[Callable] = None) -> SyncResult:
        """Sync user data for date range."""
        try:
            api_client = self._get_api_client()
            available_metrics = list(self.metric_repository.metric_tables.keys())
            
            # Separate date-based metrics from list-based metrics
            date_based_metrics = [m for m in available_metrics if m != 'activities']
            list_based_metrics = [m for m in available_metrics if m == 'activities']
            
            # Build date range for date-based metrics
            date_range = []
            current = end_date
            while current >= start_date:
                date_range.append(current)
                current -= timedelta(days=1)
            
            result = SyncResult()
            result.metrics_synced = {m: {'success': 0, 'failed': 0, 'skipped': 0} for m in available_metrics}
            
            # Calculate total items (date-based metrics + list-based metrics)
            total_items = len(date_range) * len(date_based_metrics) + len(list_based_metrics)
            completed_items = 0
            
            # Sync date-based metrics
            for date_idx, sync_date in enumerate(date_range):
                for metric_idx, metric_type in enumerate(date_based_metrics):
                    completed_items = date_idx * len(date_based_metrics) + metric_idx
                    
                    if progress_callback:
                        progress_callback({
                            'current_date': sync_date.isoformat(),
                            'current_metric': metric_type,
                            'completed_items': completed_items,
                            'total_items': total_items,
                        })
                    
                    try:
                        # Check if data exists
                        if self.metric_repository.has_metric(user_id, metric_type, sync_date):
                            result.metrics_synced[metric_type]['skipped'] += 1
                            result.total_skipped += 1
                            continue
                        
                        # Get and store data
                        accessor = api_client.metrics.get(metric_type)
                        if not accessor:
                            result.metrics_synced[metric_type]['failed'] += 1
                            result.total_failed += 1
                            continue
                        
                        data = accessor.get(sync_date.isoformat())
                        if data and self.metric_repository.store_metric(user_id, metric_type, sync_date, data):
                            result.metrics_synced[metric_type]['success'] += 1
                            result.total_success += 1
                        else:
                            result.metrics_synced[metric_type]['failed'] += 1
                            result.total_failed += 1
                    
                    except Exception as e:
                        error_msg = f"Error syncing {metric_type} for {sync_date}: {e}"
                        result.errors.append(error_msg)
                        result.metrics_synced[metric_type]['failed'] += 1
                        result.total_failed += 1
                        logger.error(error_msg)
                
                await asyncio.sleep(0.1)
            
            # Sync list-based metrics (like activities) - only once per sync
            for metric_type in list_based_metrics:
                completed_items += 1
                
                if progress_callback:
                    progress_callback({
                        'current_date': 'N/A (list-based)',
                        'current_metric': metric_type,
                        'completed_items': completed_items,
                        'total_items': total_items,
                    })
                
                try:
                    # For activities, use the end_date as the storage date
                    storage_date = end_date
                    
                    # Check if recent data exists (don't sync activities every day)
                    if self.metric_repository.has_metric(user_id, metric_type, storage_date):
                        result.metrics_synced[metric_type]['skipped'] += 1
                        result.total_skipped += 1
                        continue
                    
                    # Get activities accessor
                    accessor = api_client.metrics.get(metric_type)
                    if not accessor:
                        result.metrics_synced[metric_type]['failed'] += 1
                        result.total_failed += 1
                        continue
                    
                    # For activities, get recent activities list instead of date-specific data
                    if metric_type == 'activities':
                        data = accessor.list(limit=50)  # Get recent 50 activities
                    else:
                        data = accessor.get()  # Fallback for other list-based metrics
                    
                    if data and self.metric_repository.store_metric(user_id, metric_type, storage_date, data):
                        result.metrics_synced[metric_type]['success'] += 1
                        result.total_success += 1
                    else:
                        result.metrics_synced[metric_type]['failed'] += 1
                        result.total_failed += 1
                
                except Exception as e:
                    error_msg = f"Error syncing {metric_type}: {e}"
                    result.errors.append(error_msg)
                    result.metrics_synced[metric_type]['failed'] += 1
                    result.total_failed += 1
                    logger.error(error_msg)
            
            logger.info(f"Sync completed: {result.total_success} success, {result.total_failed} failed")
            return result
            
        except Exception as e:
            logger.error(f"Sync error: {e}")
            raise SyncError(f"Sync failed: {e}")


class LocalDB:
    """Main LocalDB facade with clean architecture."""
    
    def __init__(self, db_path: Union[str, Path]):
        self.db_manager = DatabaseManager(db_path)
        self.data_processor = DataProcessor()
        self.metric_repository = MetricRepository(self.db_manager, self.data_processor)
        self.user_repository = UserRepository(self.db_manager)
        self.sync_service = SyncService(self.metric_repository)
        
        # Initialize tables
        self.metric_repository.initialize_tables()
    
    # Delegate methods to repositories and services
    def add_user(self, user_id: str, email: str) -> None:
        """Add user to database."""
        return self.user_repository.add_user(user_id, email)
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from database."""
        return self.user_repository.get_user(user_id)
    
    def list_users(self) -> List[Dict[str, Any]]:
        """List all users."""
        return self.user_repository.list_users()
    
    def store_metric(self, user_id: str, metric_type: str, data_date: Union[str, date], api_data: Any) -> bool:
        """Store metric data."""
        return self.metric_repository.store_metric(user_id, metric_type, data_date, api_data)
    
    def get_metric(self, user_id: str, metric_type: str, data_date: Union[str, date]) -> Optional[Any]:
        """Retrieve metric data."""
        return self.metric_repository.get_metric(user_id, metric_type, data_date)
    
    def has_metric(self, user_id: str, metric_type: str, data_date: Union[str, date]) -> bool:
        """Check if metric data exists."""
        return self.metric_repository.has_metric(user_id, metric_type, data_date)
    
    async def sync_user_data(self, user_id: str, start_date: date, end_date: date, 
                            progress_callback: Optional[Callable] = None) -> SyncResult:
        """Sync user data for date range."""
        return await self.sync_service.sync_user_data(user_id, start_date, end_date, progress_callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self.db_manager.get_session() as session:
                stats = {
                    'total_metrics': len(self.metric_repository.metric_tables),
                    'users': session.query(User).count(),
                    'metrics': {}
                }
                
                total_records = 0
                for metric_name, table_class in self.metric_repository.metric_tables.items():
                    try:
                        count = session.query(table_class).count()
                        stats['metrics'][metric_name] = count
                        total_records += count
                    except Exception as table_e:
                        logger.warning(f"Cannot query {metric_name} table: {table_e}")
                        stats['metrics'][metric_name] = "schema_mismatch"
                
                stats['total_records'] = total_records
                return stats
                
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}


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
        result = await self.enhanced_db.sync_user_data(user_id, start_date, end_date, progress_callback)
        # Convert SyncResult to dict for legacy compatibility
        return {
            'total_success': result.total_success,
            'total_failed': result.total_failed,
            'total_skipped': result.total_skipped,
            'metrics_synced': result.metrics_synced,
            'errors': result.errors,
            'total_records': result.total_success
        }
    
    def get_metric_data(self, user_id: str, metric_type: str, data_date: Union[str, date]) -> Optional[Any]:
        return self.enhanced_db.get_metric(user_id, metric_type, data_date)
    
    def list_user_metrics(self, user_id: str) -> List[str]:
        """List available metrics for a user."""
        try:
            available_metrics = []
            with self.enhanced_db.db_manager.get_session() as session:
                # Check each metric table for data for this user
                for metric_name, table_class in self.enhanced_db.metric_repository.metric_tables.items():
                    try:
                        count = session.query(table_class).filter_by(user_id=user_id).count()
                        if count > 0:
                            available_metrics.append(metric_name)
                    except Exception as table_e:
                        logger.warning(f"Cannot query {metric_name} table for user {user_id}: {table_e}")
            
            return available_metrics
        except Exception as e:
            logger.error(f"Error listing user metrics for {user_id}: {e}")
            return []
    
    def get_metric_stats(self, user_id: str, metric_type: str) -> Dict[str, Any]:
        """Get statistics for a specific metric for a user."""
        try:
            if metric_type not in self.enhanced_db.metric_repository.metric_tables:
                return {"error": f"Metric {metric_type} not found"}
            
            table_class = self.enhanced_db.metric_repository.metric_tables[metric_type]
            
            with self.enhanced_db.db_manager.get_session() as session:
                from sqlalchemy import func, text
                
                # Get basic stats
                query = session.query(
                    func.count().label('total_records'),
                    func.min(table_class.data_date).label('earliest_date'),
                    func.max(table_class.data_date).label('latest_date')
                ).filter_by(user_id=user_id)
                
                result = query.first()
                
                stats = {
                    'metric_type': metric_type,
                    'total_records': result.total_records if result else 0,
                    'earliest_date': result.earliest_date.isoformat() if result and result.earliest_date else None,
                    'latest_date': result.latest_date.isoformat() if result and result.latest_date else None,
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting metric stats for {user_id}, {metric_type}: {e}")
            return {"error": str(e)}
    
    async def sync_recent_user_data(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Sync recent data for a user."""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            result = await self.enhanced_db.sync_user_data(user_id, start_date, end_date)
            
            # Convert SyncResult to dict for compatibility
            return {
                'total_success': result.total_success,
                'total_failed': result.total_failed,  
                'total_skipped': result.total_skipped,
                'metrics_synced': result.metrics_synced,
                'errors': result.errors,
                'total_records': result.total_success
            }
            
        except Exception as e:
            logger.error(f"Error syncing recent data for {user_id}: {e}")
            return {"error": str(e)}