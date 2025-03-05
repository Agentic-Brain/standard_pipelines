from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy import Column, func, DateTime, Integer, String, Boolean, event, inspect, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship, Mapper, MappedColumn
from standard_pipelines.database.exceptions import ScheduledJobError
from flask import current_app
from uuid import UUID
from standard_pipelines.extensions import db
from celery import shared_task
from time import time
from cryptography.fernet import Fernet
from bitwarden_sdk import BitwardenClient
from typing import Any, Optional, List
import json
import os

class BaseMixin(db.Model):
    __abstract__ = True
    id: Mapped[UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    modified_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Common methods
    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    # def to_dict(self):
        # return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    # def to_json(self):
        # import json
        # return json.dumps(self.to_dict())

# FIXME: This is broken, need to fix
class VersionedMixin(BaseMixin):
    __abstract__ = True
    version: Mapped[int] = mapped_column(Integer, server_default='1', default=1)

    def save(self):
        if self.version is None:
            self.version = 1
        else:
            self.version += 1
        db.session.add(self)
        db.session.commit()

class ScheduledMixin(BaseMixin):
    __abstract__ = True

    scheduled_time: Mapped[Optional[DateTime]] = mapped_column(DateTime, index=True)
    active_hours: Mapped[Optional[List[int]]] = mapped_column(JSON, default=list(range(24)))
    active_days: Mapped[Optional[List[int]]] = mapped_column(JSON, default=list(range(7)))
    recurrence_interval: Mapped[Optional[int]] = mapped_column(Integer)
    poll_interval: Mapped[Optional[int]] = mapped_column(Integer)
    next_poll_time: Mapped[Optional[DateTime]] = mapped_column(DateTime, index=True)
    run_count: Mapped[int] = mapped_column(Integer, server_default='0')
    max_runs: Mapped[Optional[int]] = mapped_column(Integer)

    @abstractmethod
    def run_job(self) -> bool:
        """Abstract method that must be implemented to trigger the actual job."""
        pass

    @abstractmethod
    def poll(self) -> bool:
        """Abstract method that must be implemented to poll for the job."""
        pass
    
    def _execute_task(self, task_callable, next_run_attr: str, interval_attr: str, update_run_count: bool = False) -> None:
        """
        Generic executor that:
          1. Calls task_callable (which should return a bool indicating success).
          2. Updates the scheduling attribute (next_run_attr) based on the interval in interval_attr.
          3. Optionally increments run count and handles max run logic.
          4. Commits the changes.
        """
        success = task_callable()
        now = datetime.utcnow()
        if success:
            # Update the "next run" field if an interval is set; otherwise, clear it.
            interval = getattr(self, interval_attr)
            if interval is not None:
                setattr(self, next_run_attr, now + timedelta(minutes=interval))
            else:
                setattr(self, next_run_attr, None)

            # For trigger jobs, update run count and check for max runs.
            if update_run_count:
                self.increment_run_count()
                if self.max_runs is not None and self.run_count >= self.max_runs:
                    setattr(self, next_run_attr, None)
                    # If this is a job, also disable recurring.
                    if next_run_attr == "scheduled_time":
                        self.recurrence_interval = None
        else:
            raise ScheduledJobError(f"Task failed for {self.__class__.__name__} {self.id}")

        db.session.commit()

    def trigger_job(self) -> None:
        """Wrapper that executes the job and updates scheduled_time based on recurrence_interval."""
        self._execute_task(self.run_job, "scheduled_time", "recurrence_interval", update_run_count=True)

    def execute_poll(self) -> None:
        """Wrapper that executes the poll and updates next_poll_time based on poll_interval."""
        self._execute_task(self.poll, "next_poll_time", "poll_interval", update_run_count=False)

    def set_scheduled_time_to_now(self) -> None:
        self.scheduled_time = datetime.utcnow()

    def delay_scheduled_time(self, delay: timedelta) -> None:
        if self.scheduled_time is None:
            self.scheduled_time = datetime.utcnow()
        self.scheduled_time += delay

    def set_scheduled_time(self, new_time: datetime) -> None:
        if new_time < datetime.utcnow():
            raise ValueError("Cannot schedule time in the past")
        self.scheduled_time = new_time

    def set_active_hours(self, hours: List[int]) -> None:
        if not hours:
            raise ValueError("Must specify at least one active hour")
        if not all(0 <= h <= 23 for h in hours):
            raise ValueError("Hours must be between 0 and 23")
        if len(set(hours)) != len(hours):
            raise ValueError("Duplicate hours are not allowed")
        self.active_hours = sorted(hours)

    def set_active_days(self, days: List[int]) -> None:
        if not days:
            raise ValueError("Must specify at least one active day")
        if not all(0 <= d <= 6 for d in days):
            raise ValueError("Days must be between 0 and 6 (Monday-Sunday)")
        if len(set(days)) != len(days):
            raise ValueError("Duplicate days are not allowed")
        self.active_days = sorted(days)

    def set_recurring(self, interval_minutes: int) -> None:
        if interval_minutes < 1:
            raise ValueError("Recurrence interval must be at least 1 minute")
        self.recurrence_interval = interval_minutes

    def stop_schedule(self) -> None:
        self.scheduled_time = None
        self.recurrence_interval = None
        self.poll_interval = None
        self.next_poll_time = None

    def disable_recurring(self) -> None:
        self.recurrence_interval = None

    def is_active_time(self, check_time: Optional[datetime] = None) -> bool:
        if check_time is None:
            check_time = datetime.utcnow()
        return (check_time.hour in self.active_hours and 
                check_time.weekday() in self.active_days)

    def increment_run_count(self) -> bool:
        """Increment run count and return True if max runs not reached."""
        self.run_count += 1
        if self.max_runs is not None and self.run_count >= self.max_runs:
            self.scheduled_time = None
            self.recurrence_interval = None
            return False
        return True

class SecureMixin(BaseMixin):
    """Mixin that provides automatic encryption for all non-primary-key fields in database."""
    __abstract__ = True
    
    # This should be implemented by child classes
    def get_encryption_key(self) -> bytes:
        """
        Override this method to specify how to retrieve the encryption key.
        Must return bytes suitable for Fernet encryption.
        """
        raise NotImplementedError("Secure models must implement get_encryption_key()")
    
    def _is_encrypted(self, value: Any) -> bool:
        """Check if a value appears to be encrypted.
        
        Fernet tokens always start with 'gAAAAA' when base64 encoded.
        Returns True if the value appears to be a Fernet token.
        """
        if value is None:
            return False
            
        # Handle both bytes and string representations
        try:
            if isinstance(value, bytes):
                return value.startswith(b'gAAAAA')
            elif isinstance(value, str):
                # Check both the string itself and its byte representation
                return value.startswith('gAAAAA') or value.encode().startswith(b'gAAAAA')
        except:
            return False
            
        return False
    
    def _encrypt_value(self, value: Any) -> str:
        """Encrypt a value and return as a string for database storage."""
        if value is None or self._is_encrypted(value):
            return value
        
        if not isinstance(value, str):
            try:
                value = json.dumps(value)
            except TypeError:
                value = str(value)
            
        fernet = Fernet(self.get_encryption_key())
        encrypted_bytes = fernet.encrypt(value.encode())
        # Convert to string for database storage
        return encrypted_bytes.decode()
    
    def _decrypt_value(self, encrypted_value: Any) -> Any:
        """Decrypt a value that might be stored as string in database."""
        if encrypted_value is None or not self._is_encrypted(encrypted_value):
            return encrypted_value
            
        try:
            fernet = Fernet(self.get_encryption_key())
            
            # Ensure we have bytes for decryption
            if isinstance(encrypted_value, str):
                encrypted_bytes = encrypted_value.encode()
            else:
                encrypted_bytes = encrypted_value
                
            decrypted = fernet.decrypt(encrypted_bytes).decode()
            try:
                return json.loads(decrypted)
            except json.JSONDecodeError:
                return decrypted
        except Exception as e:
            raise ValueError(f"Failed to decrypt value: {e}")

SKIP_ENCRYPTION_KEY : str = 'skip_encryption'

def unencrypted_mapped_column(*args, **kwargs):
    info = kwargs.pop('info', {})  # get any existing info or create a new dict
    info[SKIP_ENCRYPTION_KEY] = True
    kwargs['info'] = info
    return mapped_column(*args, **kwargs)

def __should_skip_column(column_name : str, column : MappedColumn):
    explicit_skip_columns = {'id', 'created_at', 'modified_at', 'client_id', 'user_email', 'user_name'}

    if column_name.startswith('_'):
        return True
    
    if column_name in explicit_skip_columns:
        return True
    
    if column.info.get(SKIP_ENCRYPTION_KEY, False) is True:
        return True
    
    return False

# Encrypt before saving to database
@event.listens_for(SecureMixin, 'before_insert', propagate=True)
@event.listens_for(SecureMixin, 'before_update', propagate=True)
def encrypt_before_save(mapper : Mapper, connection, target):   
    for column_name in mapper.columns.keys():
        column : MappedColumn = mapper.columns.get(column_name)

        if not __should_skip_column(column_name, column):
            value = getattr(target, column_name)
            encrypted_value = target._encrypt_value(value)
            setattr(target, column_name, encrypted_value)            

# Decrypt after loading from database
@event.listens_for(SecureMixin, 'load', propagate=True)
def decrypt_after_load(target, context):
    for column_name in inspect(target).mapper.columns.keys():
        column : Column = inspect(target).mapper.columns.get(column_name)

        if not __should_skip_column(column_name, column):
            value = getattr(target, column_name)
            decrypted_value = target._decrypt_value(value)
            setattr(target, column_name, decrypted_value)

    