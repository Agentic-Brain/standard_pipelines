from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy import func, DateTime, Integer, String, Boolean, event, inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID
from standard_pipelines.extensions import db
from time import time
from cryptography.fernet import Fernet
from bitwarden_sdk import BitwardenClient
from typing import Any
import json

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

class SecureMixin(BaseMixin):
    """Mixin that provides automatic encryption for all non-primary-key fields."""
    __abstract__ = True
    
    # Bitwarden ID for client encryption key
    encryption_key_id: Mapped[String] = mapped_column(String, nullable=False)
    _fernet: Fernet = None  # Class variable to store Fernet instance
    
    @classmethod
    def init_encryption(cls, key: bytes):
        """Initialize the encryption key for the mixin"""
        cls._encryption_key = key
        cls._fernet = Fernet(key)
    
    def _encrypt_value(self, value: Any) -> str:
        """Encrypt a value"""
        if self._fernet is None:
            raise ValueError("Encryption not initialized. Call init_encryption first.")
        
        if value is None:
            return None
            
        # Convert value to string if it isn't already
        if not isinstance(value, str):
            value = json.dumps(value)
            
        return self._fernet.encrypt(value.encode()).decode()
    
    def _decrypt_value(self, encrypted_value: str) -> Any:
        """Decrypt a value"""
        if self._fernet is None:
            raise ValueError("Encryption not initialized. Call init_encryption first.")
            
        if encrypted_value is None:
            return None
            
        try:
            decrypted = self._fernet.decrypt(encrypted_value.encode()).decode()
            try:
                # Attempt to convert back to original type
                return json.loads(decrypted)
            except json.JSONDecodeError:
                # If not JSON, return as string
                return decrypted
        except Exception as e:
            raise ValueError(f"Failed to decrypt value: {e}")
    
    def __getattribute__(self, key: str) -> Any:
        """Intercept attribute access to decrypt values"""
        # Get the actual value
        value = super().__getattribute__(key)
        
        # Don't decrypt special attributes or primary keys
        if key.startswith('_') or key == 'id' or key in ('created_at', 'modified_at'):
            return value
            
        # Get the mapper and see if this is a column
        mapper = inspect(self.__class__)
        if key in mapper.columns.keys():
            if isinstance(value, str) and value.startswith(b'gAAAAA'.decode()):
                return self._decrypt_value(value)
                
        return value
    
    def __setattr__(self, key: str, value: Any):
        """Intercept attribute setting to encrypt values"""
        # Don't encrypt special attributes or primary keys
        if key.startswith('_') or key == 'id' or key in ('created_at', 'modified_at'):
            super().__setattr__(key, value)
            return
            
        # Get the mapper and see if this is a column
        mapper = inspect(self.__class__)
        if key in mapper.columns.keys():
            # Encrypt the value before setting
            if value is not None:
                value = self._encrypt_value(value)
                
        super().__setattr__(key, value)

# Add SQLAlchemy event listeners
@event.listens_for(SecureMixin, 'before_insert', propagate=True)
def encrypt_before_insert(mapper, connection, target):
    """Ensure all appropriate fields are encrypted before insert"""
    for column in mapper.columns.keys():
        if column != 'id' and not column.startswith('_') and column not in ('created_at', 'modified_at'):
            value = getattr(target, column)
            if value is not None and not (isinstance(value, str) and value.startswith(b'gAAAAA'.decode())):
                setattr(target, column, target._encrypt_value(value))

@event.listens_for(SecureMixin, 'before_update', propagate=True)
def encrypt_before_update(mapper, connection, target):
    """Ensure all appropriate fields are encrypted before update"""
    for column in mapper.columns.keys():
        if column != 'id' and not column.startswith('_') and column not in ('created_at', 'modified_at'):
            value = getattr(target, column)
            if value is not None and not (isinstance(value, str) and value.startswith(b'gAAAAA'.decode())):
                setattr(target, column, target._encrypt_value(value))

    