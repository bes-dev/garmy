"""Core LocalDB with auto-discovery - all-in-one module."""

import asyncio
import logging
from contextlib import contextmanager
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from sqlalchemy import Column, Date, DateTime, String, Integer, Float, Text, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from ..auth.client import AuthClient
from ..core.client import APIClient
from ..core.discovery import MetricDiscovery

logger = logging.getLogger(__name__)
Base = declarative_base()


class User(Base):
    """User table."""
    __tablename__ = 'users'
    user_id = Column(String(50), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_sync = Column(DateTime, nullable=True)


def get_sqlalchemy_type(field_type):
    """Convert Python type to SQLAlchemy type."""
    type_str = str(field_type)
    if 'int' in type_str:
        return Integer
    elif 'float' in type_str:
        return Float
    elif field_type == str:
        return String(255)
    return Text


def create_model_from_dataclass(metric_name, dataclass_type):
    """Auto-generate SQLAlchemy model from dataclass."""
    attrs = {
        '__tablename__': f"{metric_name}_data",
        'user_id': Column(String(50), ForeignKey('users.user_id'), primary_key=True),
        'data_date': Column(Date, primary_key=True),
        'stored_at': Column(DateTime, default=datetime.utcnow),
    }
    
    if is_dataclass(dataclass_type):
        for field in fields(dataclass_type):
            if field.name not in ['user_id', 'data_date']:
                attrs[field.name] = Column(get_sqlalchemy_type(field.type), nullable=True)
    
    return type(f"{metric_name.title()}Data", (Base,), attrs)


def generate_models():
    """Generate all models from discovered metrics."""
    try:
        configs = MetricDiscovery.discover_metrics()
        return {name: create_model_from_dataclass(name, config.metric_class) for name, config in configs.items()}
    except Exception as e:
        logger.error(f"Failed to generate models: {e}")
        return {}


def dataclass_to_model(dataclass_instance, model_class, user_id: str, data_date):
    """Convert dataclass to model instance."""
    model_data = {'user_id': user_id, 'data_date': data_date}
    for field_name in dir(dataclass_instance):
        if not field_name.startswith('_') and hasattr(model_class, field_name):
            model_data[field_name] = getattr(dataclass_instance, field_name, None)
    return model_class(**model_data)


def model_to_dataclass(model_instance, dataclass_type):
    """Convert model instance to dataclass."""
    data = {fn: getattr(model_instance, fn, None) for fn in dir(model_instance) if not fn.startswith('_')}
    try:
        return dataclass_type(**data)
    except:
        return None


METRIC_MODELS = generate_models()


@dataclass
class SyncProgress:
    sync_id: str
    user_id: str
    status: str
    current_metric: str
    current_date: str
    total_metrics: int
    completed_metrics: int
    total_dates: int
    completed_dates: int
    start_time: datetime
    end_time: Optional[datetime] = None

    @property
    def progress_percentage(self) -> float:
        total_ops = self.total_dates * self.total_metrics
        return (self.completed_metrics / total_ops * 100) if total_ops > 0 else 0.0


class LocalDataStore:
    """Auto-discovery based data store."""

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.engine = create_engine(f"sqlite:///{self.db_path}", connect_args={'check_same_thread': False})
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.metric_configs = MetricDiscovery.discover_metrics()

    @contextmanager
    def get_session(self) -> Session:
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
        with self.get_session() as session:
            session.merge(User(user_id=user_id, email=email))

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self.get_session() as session:
            user = session.query(User).filter_by(user_id=user_id).first()
            return {'user_id': user.user_id, 'email': user.email} if user else None

    def list_users(self) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            return [{'user_id': u.user_id, 'email': u.email} for u in session.query(User).all()]

    def store_metric(self, user_id: str, metric_type: str, data_date: Union[str, date], dataclass_instance: Any) -> None:
        if isinstance(data_date, str):
            data_date = datetime.strptime(data_date, "%Y-%m-%d").date()

        model_class = METRIC_MODELS.get(metric_type)
        if not model_class:
            return

        with self.get_session() as session:
            try:
                model_instance = dataclass_to_model(dataclass_instance, model_class, user_id, data_date)
                session.merge(model_instance)
            except Exception:
                return

    def get_metric(self, user_id: str, metric_type: str, data_date: Union[str, date]) -> Optional[Any]:
        if isinstance(data_date, str):
            data_date = datetime.strptime(data_date, "%Y-%m-%d").date()

        model_class = METRIC_MODELS.get(metric_type)
        config = self.metric_configs.get(metric_type)
        if not model_class or not config:
            return None

        with self.get_session() as session:
            model_instance = session.query(model_class).filter_by(user_id=user_id, data_date=data_date).first()
            return model_to_dataclass(model_instance, config.metric_class) if model_instance else None

    def list_metric_dates(self, user_id: str, metric_type: str, start_date: Optional[Union[str, date]] = None, end_date: Optional[Union[str, date]] = None) -> List[str]:
        model_class = METRIC_MODELS.get(metric_type)
        if not model_class:
            return []

        with self.get_session() as session:
            query = session.query(model_class.data_date).filter_by(user_id=user_id)
            
            if start_date:
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                query = query.filter(model_class.data_date >= start_date)
                
            if end_date:
                if isinstance(end_date, str):
                    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                query = query.filter(model_class.data_date <= end_date)
            
            return [d[0].isoformat() for d in query.all()]

    def update_last_sync(self, user_id: str) -> None:
        with self.get_session() as session:
            user = session.query(User).filter_by(user_id=user_id).first()
            if user:
                user.last_sync = datetime.utcnow()

    def get_database_stats(self) -> Dict[str, Any]:
        with self.get_session() as session:
            stats = {'users': session.query(User).count(), 'metrics': {}}
            for metric_type, model_class in METRIC_MODELS.items():
                stats['metrics'][metric_type] = session.query(model_class).count()
            stats['total_records'] = sum(stats['metrics'].values())
            return stats


class SyncManager:
    """Compact sync manager using auto-discovery."""

    def __init__(self, api_client: APIClient, storage: LocalDataStore, user_id: str):
        self.api_client = api_client
        self.storage = storage
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)
        self._active_syncs: Dict[str, SyncProgress] = {}
        self._existing_cache: Dict[str, set] = {}

    def _get_available_metrics(self) -> List[str]:
        try:
            configs = MetricDiscovery.discover_metrics()
            all_metrics = list(configs.keys())
            if hasattr(self.api_client, 'metrics'):
                api_metrics = set(self.api_client.metrics.keys())
                return list(set(all_metrics).intersection(api_metrics))
            return all_metrics
        except Exception:
            return ['steps', 'heart_rate', 'sleep']

    async def sync_all_metrics(self, start_date: date, end_date: date, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        sync_id = f"{self.user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        metrics = [m for m in self._get_available_metrics() if m != 'activities']
        
        if not metrics:
            return {'error': 'No metrics available'}

        # Build cache
        self._existing_cache.clear()
        for metric in metrics:
            dates = self.storage.list_metric_dates(self.user_id, metric, start_date, end_date)
            self._existing_cache[metric] = {datetime.strptime(d, "%Y-%m-%d").date() for d in dates}

        date_range = []
        current = end_date
        while current >= start_date:
            date_range.append(current)
            current -= timedelta(days=1)

        progress = SyncProgress(
            sync_id=sync_id, user_id=self.user_id, status='running',
            current_metric='', current_date='',
            total_metrics=len(metrics), completed_metrics=0,
            total_dates=len(date_range), completed_dates=0,
            start_time=datetime.utcnow()
        )
        self._active_syncs[sync_id] = progress

        results = {
            'sync_id': sync_id,
            'metrics_synced': {m: {'records_synced': 0, 'records_skipped': 0} for m in metrics},
            'total_records': 0, 'errors': []
        }

        try:
            for date_idx, sync_date in enumerate(date_range):
                progress.current_date = sync_date.isoformat()
                
                for metric_idx, metric_type in enumerate(metrics):
                    progress.current_metric = metric_type
                    progress.completed_metrics = date_idx * len(metrics) + metric_idx
                    
                    if progress_callback:
                        progress_callback(progress)

                    # Skip if exists
                    if sync_date in self._existing_cache.get(metric_type, set()):
                        results['metrics_synced'][metric_type]['records_skipped'] += 1
                        continue

                    try:
                        accessor = self.api_client.metrics.get(metric_type)
                        if accessor:
                            data = accessor.get(sync_date.isoformat())
                            if data:
                                # Extract appropriate data for storage
                                storage_data = self._extract_data(data)
                                if storage_data:
                                    self.storage.store_metric(self.user_id, metric_type, sync_date, storage_data)
                                    results['metrics_synced'][metric_type]['records_synced'] += 1
                                    results['total_records'] += 1
                    except Exception as e:
                        results['errors'].append(f"Error syncing {metric_type} for {sync_date}: {e}")

                await asyncio.sleep(0.1)

            progress.status = 'completed'
            progress.end_time = datetime.utcnow()
            self.storage.update_last_sync(self.user_id)
            return results

        except Exception as e:
            progress.status = 'failed'
            progress.end_time = datetime.utcnow()
            raise
        finally:
            if progress_callback:
                progress_callback(progress)

    def _extract_data(self, data: Any) -> Any:
        """Extract storable data from API response."""
        if hasattr(data, '__dataclass_fields__'):
            return data
        if hasattr(data, 'daily_steps') and data.daily_steps:
            return data.daily_steps[0]
        if hasattr(data, 'heart_rate_summary'):
            return data.heart_rate_summary
        if hasattr(data, 'sleep_summary'):
            return data.sleep_summary
        return data

    def get_sync_progress(self, sync_id: str) -> Optional[SyncProgress]:
        return self._active_syncs.get(sync_id)


class LocalDBClient:
    """Compact LocalDB client."""

    def __init__(self, db_path: Union[str, Path]):
        self.storage = LocalDataStore(Path(db_path).expanduser())
        self._auth_client = None
        self._api_client = None
        self._sync_managers = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def add_user(self, user_id: str, email: str) -> None:
        self.storage.add_user(user_id, email)

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.storage.get_user(user_id)

    def list_users(self) -> List[Dict[str, Any]]:
        return self.storage.list_users()

    def get_database_stats(self) -> Dict[str, Any]:
        return self.storage.get_database_stats()

    def _get_api_client(self) -> APIClient:
        if not self._api_client:
            if not self._auth_client:
                self._auth_client = AuthClient()
            self._api_client = APIClient(auth_client=self._auth_client)
        return self._api_client

    def _get_sync_manager(self, user_id: str) -> SyncManager:
        if user_id not in self._sync_managers:
            api_client = self._get_api_client()
            self._sync_managers[user_id] = SyncManager(api_client, self.storage, user_id)
        return self._sync_managers[user_id]

    async def sync_user_data(self, user_id: str, start_date: date, end_date: date, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        sync_manager = self._get_sync_manager(user_id)
        return await sync_manager.sync_all_metrics(start_date, end_date, progress_callback)

    def get_metric_data(self, user_id: str, metric_type: str, data_date: Union[str, date]) -> Optional[Any]:
        return self.storage.get_metric(user_id, metric_type, data_date)

    def list_metric_dates(self, user_id: str, metric_type: str, start_date: Optional[Union[str, date]] = None, end_date: Optional[Union[str, date]] = None) -> List[str]:
        return self.storage.list_metric_dates(user_id, metric_type, start_date, end_date)