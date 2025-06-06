"""SQLAlchemy storage implementation with automatic dataclass mapping."""

from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union, Type
from contextlib import contextmanager
from pathlib import Path
from dataclasses import is_dataclass

from sqlalchemy import create_engine, and_, desc, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from .models import (
    Base, User, StepsData, HeartRateData, SleepData, BodyBatteryData,
    ActivitiesData, CaloriesData, DailySummaryData, HrvData, 
    RespirationData, StressData, TrainingReadinessData,
    dataclass_to_model, model_to_dataclass
)
from ..metrics.steps import DailySteps
from ..metrics.heart_rate import HeartRateSummary  
from ..metrics.sleep import SleepSummary
from ..metrics.activities import ActivitySummary
from ..metrics.calories import Calories
from ..metrics.daily_summary import DailySummary
from ..metrics.hrv import HRVSummary
from ..metrics.respiration import RespirationSummary
from ..metrics.stress import Stress
from ..metrics.training_readiness import TrainingReadiness


class LocalDataStore:
    """SQLAlchemy data store with automatic dataclass mapping."""
    
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create engine with optimizations
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={
                'check_same_thread': False,
                'timeout': 30
            },
            pool_pre_ping=True,
            echo=False
        )
        
        # Create tables
        Base.metadata.create_all(self.engine)
        
        # Session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Session:
        """Get database session with automatic commit/rollback."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def close(self):
        """Close storage and cleanup connections."""
        self.engine.dispose()
    
    # User operations
    def add_user(self, user_id: str, email: str, display_name: str = None, auth_token_path: str = None) -> None:
        """Add user to database."""
        with self.get_session() as session:
            user = User(
                user_id=user_id,
                email=email,
                display_name=display_name,
                auth_token_path=auth_token_path,
                created_at=datetime.utcnow()
            )
            session.add(user)
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        with self.get_session() as session:
            user = session.query(User).filter_by(user_id=user_id).first()
            if not user:
                return None
            
            return {
                'user_id': user.user_id,
                'email': user.email,
                'display_name': user.display_name,
                'auth_token_path': user.auth_token_path,
                'created_at': user.created_at,
                'last_sync': user.last_sync
            }
    
    def list_users(self) -> List[Dict[str, Any]]:
        """List all users."""
        with self.get_session() as session:
            users = session.query(User).all()
            return [
                {
                    'user_id': user.user_id,
                    'email': user.email,
                    'display_name': user.display_name,
                    'auth_token_path': user.auth_token_path,
                    'created_at': user.created_at,
                    'last_sync': user.last_sync
                }
                for user in users
            ]
    
    def remove_user(self, user_id: str) -> None:
        """Remove user and all their data."""
        with self.get_session() as session:
            user = session.query(User).filter_by(user_id=user_id).first()
            if user:
                session.delete(user)
    
    def update_last_sync(self, user_id: str) -> None:
        """Update user's last sync timestamp."""
        with self.get_session() as session:
            user = session.query(User).filter_by(user_id=user_id).first()
            if user:
                user.last_sync = datetime.utcnow()
    
    # Generic metric operations
    def store_metric(self, user_id: str, metric_type: str, data_date: Union[str, date], dataclass_instance: Any) -> None:
        """Store metric data using dataclass to model conversion."""
        if isinstance(data_date, str):
            data_date = datetime.strptime(data_date, "%Y-%m-%d").date()
        
        # Map metric type to model class and dataclass type
        type_mapping = {
            'steps': (StepsData, DailySteps),
            'heart_rate': (HeartRateData, HeartRateSummary), 
            'sleep': (SleepData, SleepSummary),
            'body_battery': (BodyBatteryData, None),  # Handle separately
            'activities': (ActivitiesData, ActivitySummary),
            'calories': (CaloriesData, Calories),
            'daily_summary': (DailySummaryData, DailySummary),
            'hrv': (HrvData, HRVSummary),
            'respiration': (RespirationData, RespirationSummary),
            'stress': (StressData, Stress),
            'training_readiness': (TrainingReadinessData, TrainingReadiness)
        }
        
        if metric_type not in type_mapping:
            # Silently skip unsupported metrics instead of failing
            return
        
        model_class, expected_dataclass = type_mapping[metric_type]
        
        # Validate that dataclass_instance is actually a dataclass
        if not is_dataclass(dataclass_instance):
            raise ValueError(f"Expected dataclass for {metric_type}, got {type(dataclass_instance)}: {dataclass_instance}")
        
        with self.get_session() as session:
            # Create or update record (SQLite will handle PRIMARY KEY conflicts)
            try:
                model_instance = dataclass_to_model(dataclass_instance, model_class, user_id, data_date)
                session.merge(model_instance)  # merge() handles INSERT or UPDATE automatically
            except Exception as e:
                if "no meaningful data" in str(e):
                    # Skip records with no meaningful data to preserve statistics integrity
                    return
                elif "NOT NULL constraint failed" in str(e):
                    # Don't create fake records - just skip incomplete data
                    return
                else:
                    raise
    
    def get_metric(self, user_id: str, metric_type: str, data_date: Union[str, date]) -> Optional[Any]:
        """Get metric data and convert back to dataclass."""
        if isinstance(data_date, str):
            data_date = datetime.strptime(data_date, "%Y-%m-%d").date()
        
        type_mapping = {
            'steps': (StepsData, DailySteps),
            'heart_rate': (HeartRateData, HeartRateSummary), 
            'sleep': (SleepData, SleepSummary),
            'body_battery': (BodyBatteryData, None),  # Handle separately
            'activities': (ActivitiesData, ActivitySummary),
            'calories': (CaloriesData, Calories),
            'daily_summary': (DailySummaryData, DailySummary),
            'hrv': (HrvData, HRVSummary),
            'respiration': (RespirationData, RespirationSummary),
            'stress': (StressData, Stress),
            'training_readiness': (TrainingReadinessData, TrainingReadiness)
        }
        
        if metric_type not in type_mapping:
            return None
        
        model_class, dataclass_type = type_mapping[metric_type]
        
        with self.get_session() as session:
            model_instance = session.query(model_class).filter_by(
                user_id=user_id,
                data_date=data_date
            ).first()
            
            if not model_instance:
                return None
            
            if dataclass_type:
                return model_to_dataclass(model_instance, dataclass_type)
            else:
                # Return raw model data for body_battery
                return {attr: getattr(model_instance, attr) for attr in model_instance.__dict__ if not attr.startswith('_')}
    
    def list_metric_dates(self, user_id: str, metric_type: str, start_date: Optional[Union[str, date]] = None, end_date: Optional[Union[str, date]] = None) -> List[str]:
        """List available dates for a metric."""
        type_mapping = {
            'steps': StepsData,
            'heart_rate': HeartRateData,
            'sleep': SleepData,
            'body_battery': BodyBatteryData,
            'activities': ActivitiesData,
            'calories': CaloriesData,
            'daily_summary': DailySummaryData,
            'hrv': HrvData,
            'respiration': RespirationData,
            'stress': StressData,
            'training_readiness': TrainingReadinessData
        }
        
        if metric_type not in type_mapping:
            return []
        
        model_class = type_mapping[metric_type]
        
        with self.get_session() as session:
            # Activities use activity_date, other metrics use data_date
            if metric_type == 'activities':
                date_field = model_class.activity_date
            else:
                date_field = model_class.data_date
                
            query = session.query(date_field).filter_by(user_id=user_id)
            
            if start_date:
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                query = query.filter(date_field >= start_date)
            
            if end_date:
                if isinstance(end_date, str):
                    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                query = query.filter(date_field <= end_date)
            
            dates = query.order_by(date_field).all()
            return [d[0].isoformat() for d in dates]
    
    def list_user_metrics(self, user_id: str) -> List[str]:
        """List available metric types for user."""
        available_metrics = []
        
        # Dynamic mapping of all supported metrics
        metric_models = {
            'steps': StepsData,
            'heart_rate': HeartRateData,
            'sleep': SleepData,
            'body_battery': BodyBatteryData,
            'activities': ActivitiesData,
            'calories': CaloriesData,
            'daily_summary': DailySummaryData,
            'hrv': HrvData,
            'respiration': RespirationData,
            'stress': StressData,
            'training_readiness': TrainingReadinessData
        }
        
        with self.get_session() as session:
            # Check each metric type dynamically
            for metric_name, model_class in metric_models.items():
                if session.query(model_class).filter_by(user_id=user_id).first():
                    available_metrics.append(metric_name)
        
        return available_metrics
    
    # Activities operations (special handling)
    def store_activity(self, user_id: str, activity: ActivitySummary) -> None:
        """Store individual activity."""
        import json
        from datetime import datetime
        
        with self.get_session() as session:
            # Check if activity already exists
            existing = session.query(ActivitiesData).filter_by(
                user_id=user_id,
                activity_id=activity.activity_id
            ).first()
            
            if existing:
                # Update existing activity
                existing.activity_date = datetime.strptime(activity.start_date, '%Y-%m-%d').date()
                existing.activity_data = json.dumps(activity.__dict__, default=str)
                existing.stored_at = datetime.utcnow()
            else:
                # Create new activity record
                activity_record = ActivitiesData(
                    user_id=user_id,
                    activity_id=activity.activity_id,
                    activity_date=datetime.strptime(activity.start_date, '%Y-%m-%d').date(),
                    activity_data=json.dumps(activity.__dict__, default=str)
                )
                session.add(activity_record)
    
    def get_activities_for_date_range(self, user_id: str, start_date: date, end_date: date) -> List[ActivitySummary]:
        """Get activities for date range."""
        import json
        
        with self.get_session() as session:
            activities = session.query(ActivitiesData).filter(
                ActivitiesData.user_id == user_id,
                ActivitiesData.activity_date >= start_date,
                ActivitiesData.activity_date <= end_date
            ).order_by(ActivitiesData.activity_date.desc()).all()
            
            result = []
            for activity_record in activities:
                activity_dict = json.loads(activity_record.activity_data)
                activity = ActivitySummary(**activity_dict)
                result.append(activity)
            
            return result
    
    def get_activities_count(self, user_id: str) -> int:
        """Get total activities count for user."""
        with self.get_session() as session:
            return session.query(ActivitiesData).filter_by(user_id=user_id).count()
    
    # Analytics operations
    def get_metric_stats(self, user_id: str, metric_type: str) -> Dict[str, Any]:
        """Get analytics stats for a metric."""
        type_mapping = {
            'steps': StepsData,
            'heart_rate': HeartRateData,
            'sleep': SleepData,
            'body_battery': BodyBatteryData
        }
        
        if metric_type not in type_mapping:
            return {}
        
        model_class = type_mapping[metric_type]
        
        with self.get_session() as session:
            query = session.query(model_class).filter_by(user_id=user_id)
            total_records = query.count()
            
            if total_records == 0:
                return {'total_records': 0}
            
            # Get date range
            min_date = query.order_by(model_class.data_date).first().data_date
            max_date = query.order_by(desc(model_class.data_date)).first().data_date
            
            stats = {
                'total_records': total_records,
                'date_range': {
                    'start': min_date.isoformat(),
                    'end': max_date.isoformat(),
                    'days': (max_date - min_date).days + 1
                }
            }
            
            # Metric-specific statistics
            if metric_type == 'steps':
                avg_steps = session.query(func.avg(model_class.total_steps)).filter_by(user_id=user_id).scalar()
                max_steps = session.query(func.max(model_class.total_steps)).filter_by(user_id=user_id).scalar()
                total_distance = session.query(func.sum(model_class.total_distance)).filter_by(user_id=user_id).scalar()
                
                stats.update({
                    'average_daily_steps': int(avg_steps) if avg_steps else 0,
                    'max_daily_steps': max_steps or 0,
                    'total_distance_km': (total_distance / 1000) if total_distance else 0
                })
            
            elif metric_type == 'heart_rate':
                avg_resting = session.query(func.avg(model_class.resting_heart_rate)).filter_by(user_id=user_id).scalar()
                stats.update({
                    'average_resting_hr': int(avg_resting) if avg_resting else 0
                })
            
            elif metric_type == 'sleep':
                avg_sleep = session.query(func.avg(model_class.sleep_time_seconds)).filter_by(user_id=user_id).scalar()
                avg_efficiency = session.query(func.avg(model_class.sleep_efficiency_percentage)).filter_by(user_id=user_id).scalar()
                stats.update({
                    'average_sleep_hours': (avg_sleep / 3600) if avg_sleep else 0,
                    'average_efficiency': avg_efficiency or 0
                })
            
            return stats
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get overall database statistics."""
        with self.get_session() as session:
            user_count = session.query(User).count()
            
            stats = {
                'users': user_count,
                'metrics': {}
            }
            
            # Count records for each metric type
            for metric_type, model_class in [
                ('steps', StepsData),
                ('heart_rate', HeartRateData), 
                ('sleep', SleepData),
                ('body_battery', BodyBatteryData)
            ]:
                count = session.query(model_class).count()
                stats['metrics'][metric_type] = count
            
            stats['total_records'] = sum(stats['metrics'].values())
            
            return stats