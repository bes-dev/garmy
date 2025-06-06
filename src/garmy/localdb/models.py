"""Auto-generated SQLAlchemy models from metrics dataclasses."""

import json
from datetime import datetime, date
from typing import Any, Dict, Optional, get_type_hints, Union, List
from dataclasses import dataclass, fields, is_dataclass
import inspect

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Date, Boolean, Text, 
    ForeignKey, Index, BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Import all metrics dataclasses
from ..metrics.steps import DailySteps, StepsAggregations
from ..metrics.heart_rate import HeartRateSummary
from ..metrics.sleep import SleepSummary  
from ..metrics.body_battery import BodyBatteryReading
from ..metrics.activities import ActivitySummary
from ..metrics.calories import Calories
from ..metrics.daily_summary import DailySummary
from ..metrics.hrv import HRVSummary
from ..metrics.respiration import RespirationSummary
from ..metrics.stress import Stress
from ..metrics.training_readiness import TrainingReadiness

Base = declarative_base()


def get_sqlalchemy_type(field_type, field_name: str = ""):
    """Convert Python type to SQLAlchemy type."""
    # Handle Optional types
    if hasattr(field_type, '__origin__') and field_type.__origin__ is Union:
        args = field_type.__args__
        if len(args) == 2 and type(None) in args:
            # Optional[X] = Union[X, None]
            field_type = args[0] if args[1] is type(None) else args[1]
    
    # Basic type mapping
    if field_type == int:
        if 'timestamp' in field_name.lower():
            return BigInteger
        return Integer
    elif field_type == float:
        return Float
    elif field_type == str:
        if 'email' in field_name.lower():
            return String(255)
        elif 'path' in field_name.lower():
            return String(500)
        elif 'feedback' in field_name.lower() or 'insight' in field_name.lower():
            return String(500)
        elif len(field_name) > 20:  # Long field names likely need more space
            return String(500)
        return String(50)
    elif field_type == bool:
        return Boolean
    elif field_type == datetime:
        return DateTime
    elif field_type == date:
        return Date
    elif field_type == dict or 'Dict' in str(field_type):
        return Text  # Store as JSON
    elif field_type == list or 'List' in str(field_type):
        return Text  # Store as JSON
    else:
        return Text  # Default fallback


def create_table_from_dataclass(dataclass_type, table_name: str, user_foreign_key: bool = True):
    """Create SQLAlchemy table class from dataclass."""
    
    # Get dataclass fields
    dc_fields = fields(dataclass_type)
    
    # Get type hints with proper namespace including datetime and other common types
    try:
        # Create namespace with common types that might be referenced in dataclasses
        namespace = {
            'datetime': datetime,
            'date': date, 
            'Optional': Optional,
            'Union': Union,
            'List': List,
            'Dict': Dict,
            'Any': Any
        }
        namespace.update(globals())
        type_hints = get_type_hints(dataclass_type, globalns=namespace)
    except (NameError, AttributeError) as e:
        # Fallback to field.type if get_type_hints fails
        type_hints = {field.name: field.type for field in dc_fields}
    
    # Create table attributes
    table_attrs = {
        '__tablename__': table_name,
        '__table_args__': ()
    }
    
    # Add user_id and data_date as composite primary key
    if user_foreign_key:
        table_attrs['user_id'] = Column(String(50), ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
        table_attrs['data_date'] = Column(Date, primary_key=True)
        table_attrs['user'] = relationship("User", back_populates=table_name.replace('_data', ''))
    
    # Convert dataclass fields to SQLAlchemy columns
    for field in dc_fields:
        field_type = type_hints.get(field.name, field.type)
        column_type = get_sqlalchemy_type(field_type, field.name)
        
        # Skip properties and private fields
        if field.name.startswith('_'):
            continue
            
        # All fields should be nullable by default to handle API inconsistencies
        nullable = True
        
        table_attrs[field.name] = Column(column_type, nullable=nullable)
    
    # Add metadata
    table_attrs['stored_at'] = Column(DateTime, default=datetime.utcnow)
    
    # Add indexes
    if user_foreign_key:
        table_attrs['__table_args__'] = (
            Index(f'idx_{table_name}_user_date', 'user_id', 'data_date'),
            Index(f'idx_{table_name}_date', 'data_date'),
        )
    
    # Create and return the table class
    return type(table_name.title().replace('_', ''), (Base,), table_attrs)


# Base User table
class User(Base):
    """User model."""
    __tablename__ = 'users'
    
    user_id = Column(String(50), primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255))
    auth_token_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_sync = Column(DateTime)
    
    # Relationships will be added dynamically


# Auto-generate tables from dataclasses
StepsData = create_table_from_dataclass(DailySteps, 'steps_data')
HeartRateData = create_table_from_dataclass(HeartRateSummary, 'heart_rate_data') 
SleepData = create_table_from_dataclass(SleepSummary, 'sleep_data')
CaloriesData = create_table_from_dataclass(Calories, 'calories_data')
DailySummaryData = create_table_from_dataclass(DailySummary, 'daily_summary_data')
HrvData = create_table_from_dataclass(HRVSummary, 'hrv_data')
RespirationData = create_table_from_dataclass(RespirationSummary, 'respiration_data')
StressData = create_table_from_dataclass(Stress, 'stress_data')
TrainingReadinessData = create_table_from_dataclass(TrainingReadiness, 'training_readiness_data')

# Activities table with special structure (activity_id as primary key instead of date)
def create_activities_table():
    """Create custom activities table with activity_id primary key."""
    from sqlalchemy import Column, String, Integer, Date, Text, DateTime, ForeignKey, Index
    from sqlalchemy.orm import relationship
    
    class ActivitiesData(Base):
        __tablename__ = 'activities_data'
        
        # Composite primary key: user_id + activity_id
        user_id = Column(String(50), ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
        activity_id = Column(Integer, primary_key=True)
        
        # Activity date for filtering and joins
        activity_date = Column(Date, nullable=False, index=True)
        
        # Store complete ActivitySummary as JSON
        activity_data = Column(Text, nullable=False)
        
        # Metadata
        stored_at = Column(DateTime, default=datetime.utcnow)
        
        # Relationships
        user = relationship("User", back_populates="activities")
        
        # Indexes for performance
        __table_args__ = (
            Index('idx_activities_user_date', 'user_id', 'activity_date'),
            Index('idx_activities_date', 'activity_date'),
        )
    
    return ActivitiesData

ActivitiesData = create_activities_table()

# Import BodyBatterySummary from metrics module
from ..metrics.body_battery import BodyBatterySummary
BodyBatteryData = create_table_from_dataclass(BodyBatterySummary, 'body_battery_data')

# Add relationships to User
User.steps = relationship("StepsData", back_populates="user", cascade="all, delete-orphan")
User.heart_rate = relationship("HeartRateData", back_populates="user", cascade="all, delete-orphan")  
User.sleep = relationship("SleepData", back_populates="user", cascade="all, delete-orphan")
User.body_battery = relationship("BodyBatteryData", back_populates="user", cascade="all, delete-orphan")
User.activities = relationship("ActivitiesData", back_populates="user", cascade="all, delete-orphan")
User.calories = relationship("CaloriesData", back_populates="user", cascade="all, delete-orphan")
User.daily_summary = relationship("DailySummaryData", back_populates="user", cascade="all, delete-orphan")
User.hrv = relationship("HrvData", back_populates="user", cascade="all, delete-orphan")
User.respiration = relationship("RespirationData", back_populates="user", cascade="all, delete-orphan")
User.stress = relationship("StressData", back_populates="user", cascade="all, delete-orphan")
User.training_readiness = relationship("TrainingReadinessData", back_populates="user", cascade="all, delete-orphan")


def serialize_field(value: Any) -> str:
    """Serialize complex field to JSON string."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    elif is_dataclass(value):
        # Convert dataclass to dict and then serialize
        from dataclasses import asdict
        return json.dumps(asdict(value), default=str)
    return str(value)


def deserialize_field(value: str, target_type: type) -> Any:
    """Deserialize JSON string back to original type."""
    if not value:
        return None if 'Optional' in str(target_type) else ([] if 'List' in str(target_type) else {})
    
    try:
        if 'List' in str(target_type) or 'Dict' in str(target_type):
            return json.loads(value)
        # For dataclass types, try to reconstruct from JSON
        elif hasattr(target_type, '__dataclass_fields__'):
            data = json.loads(value)
            return target_type(**data)
        return value
    except (json.JSONDecodeError, TypeError):
        return value


def dataclass_to_model(dataclass_instance, model_class, user_id: str, data_date: date):
    """Convert dataclass instance to SQLAlchemy model instance."""
    
    model_data = {
        'user_id': user_id,
        'data_date': data_date
    }
    
    # Check if this dataclass has actual data or is mostly empty defaults
    has_meaningful_data = False
    
    # Convert dataclass fields to model data
    for field in fields(dataclass_instance):
        # Skip fields that don't exist in the model
        if not hasattr(model_class, field.name):
            continue
            
        value = getattr(dataclass_instance, field.name, None)
        
        # Check for meaningful data (not None, not empty string, not zero for critical fields)
        if field.name in ['weekly_avg', 'last_night_avg', 'avg_waking_respiration_value', 'avg_sleep_respiration_value']:
            if value is not None and value != 0 and value != "":
                has_meaningful_data = True
        
        # Special check for HRV data - meaningful data is in hrv_summary sub-object
        if field.name == 'hrv_summary' and value is not None:
            if hasattr(value, 'weekly_avg') and value.weekly_avg and value.weekly_avg != 0:
                has_meaningful_data = True
            if hasattr(value, 'last_night_avg') and value.last_night_avg and value.last_night_avg != 0:
                has_meaningful_data = True
        
        # Special check for Body Battery data - meaningful data is in body_battery_values_array
        if field.name == 'body_battery_values_array' and value is not None:
            if isinstance(value, list) and len(value) > 0:
                has_meaningful_data = True
        
        # Handle None values and empty strings
        if value is None or value == "":
            if field.default != field.default_factory:
                value = field.default
            elif field.name == 'calendar_date':
                value = data_date.isoformat()  # Critical for queries
            elif field.name == 'user_profile_pk':
                value = 0  # Critical metadata
            # For other fields, keep None and let nullable handle it
        
        # Convert datetime strings
        if isinstance(value, str) and 'timestamp' in field.name.lower():
            try:
                from datetime import datetime
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                pass
        
        # Store the value
        if isinstance(value, (dict, list)):
            model_data[field.name] = serialize_field(value)
        elif is_dataclass(value):
            # Serialize nested dataclasses (like HRVBaseline)
            model_data[field.name] = serialize_field(value)
        else:
            model_data[field.name] = value
    
    # FORCE ADD missing critical fields that model requires but dataclass doesn't have
    if hasattr(model_class, 'calendar_date') and 'calendar_date' not in model_data:
        model_data['calendar_date'] = data_date.isoformat()
        
    if hasattr(model_class, 'user_profile_pk') and 'user_profile_pk' not in model_data:
        # Try to get from dataclass first
        profile_pk = getattr(dataclass_instance, 'user_profile_pk', None)
        if profile_pk is not None:
            model_data['user_profile_pk'] = profile_pk
        else:
            model_data['user_profile_pk'] = 0
    
    # Skip creating records that have no meaningful data to preserve data integrity
    if not has_meaningful_data:
        metric_name = type(dataclass_instance).__name__
        raise ValueError(f"Skipping {metric_name} for {data_date} - no meaningful data (preserves statistics integrity)")
    
    return model_class(**model_data)


def model_to_dataclass(model_instance, dataclass_type):
    """Convert SQLAlchemy model instance back to dataclass."""
    dc_fields = fields(dataclass_type)
    type_hints = get_type_hints(dataclass_type)
    
    data = {}
    for field in dc_fields:
        value = getattr(model_instance, field.name, None)
        field_type = type_hints.get(field.name, field.type)
        
        # Deserialize complex types
        if isinstance(value, str) and ('List' in str(field_type) or 'Dict' in str(field_type)):
            data[field.name] = deserialize_field(value, field_type)
        else:
            data[field.name] = value
    
    return dataclass_type(**data)