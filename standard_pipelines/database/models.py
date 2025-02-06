from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy import func, DateTime, Integer, String, Boolean, event, inspect, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID
from standard_pipelines.extensions import db
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

class ScheduledMixin(BaseMixin, ABC):
    __abstract__ = True

    scheduled_time: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True, index=True)
    active_hours: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True, default=list(range(24)))
    active_days: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True, default=list(range(7)))
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recurrence_interval: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_runs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    @abstractmethod
    def trigger_job(self) -> None:
        """Abstract method that must be implemented to trigger the actual job."""
        pass

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
        self.is_recurring = True
        self.recurrence_interval = interval_minutes

    def disable_recurring(self) -> None:
        self.is_recurring = False
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
            self.is_recurring = False
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

# Encrypt before saving to database
@event.listens_for(SecureMixin, 'before_insert', propagate=True)
@event.listens_for(SecureMixin, 'before_update', propagate=True)
def encrypt_before_save(mapper, connection, target):
    skip_columns = {'id', 'created_at', 'modified_at', 'client_id'}
    
    for column in mapper.columns.keys():
        if not column.startswith('_') and column not in skip_columns:
            value = getattr(target, column)
            encrypted_value = target._encrypt_value(value)
            setattr(target, column, encrypted_value)

# Decrypt after loading from database
@event.listens_for(SecureMixin, 'load', propagate=True)
def decrypt_after_load(target, context):
    skip_columns = {'id', 'created_at', 'modified_at', 'client_id'}
    
    for column in inspect(target).mapper.columns.keys():
        if not column.startswith('_') and column not in skip_columns:
            value = getattr(target, column)
            decrypted_value = target._decrypt_value(value)
            setattr(target, column, decrypted_value)

    