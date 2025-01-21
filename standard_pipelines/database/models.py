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
        if not isinstance(value, (str, bytes)):
            return False
        try:
            return (isinstance(value, bytes) and value.startswith(b'gAAAAA')) or \
                   (isinstance(value, str) and value.startswith('gAAAAA'))
        except:
            return False
    
    def _encrypt_value(self, value: Any) -> bytes:
        if value is None or self._is_encrypted(value):
            return value
        
        if not isinstance(value, str):
            try:
                value = json.dumps(value)
            except TypeError:
                value = str(value)
            
        fernet = Fernet(self.get_encryption_key())
        return fernet.encrypt(value.encode())
    
    def _decrypt_value(self, encrypted_value: bytes | str) -> Any:
        if encrypted_value is None or not self._is_encrypted(encrypted_value):
            return encrypted_value
            
        try:
            fernet = Fernet(self.get_encryption_key())
            if isinstance(encrypted_value, str):
                encrypted_value = encrypted_value.encode()
            decrypted = fernet.decrypt(encrypted_value).decode()
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
    skip_columns = {'id', 'created_at', 'modified_at'}
    
    for column in mapper.columns.keys():
        if not column.startswith('_') and column not in skip_columns:
            value = getattr(target, column)
            encrypted_value = target._encrypt_value(value)
            setattr(target, column, encrypted_value)

# Decrypt after loading from database
@event.listens_for(SecureMixin, 'load', propagate=True)
def decrypt_after_load(target, context):
    skip_columns = {'id', 'created_at', 'modified_at'}
    
    for column in inspect(target).mapper.columns.keys():
        if not column.startswith('_') and column not in skip_columns:
            value = getattr(target, column)
            decrypted_value = target._decrypt_value(value)
            setattr(target, column, decrypted_value)

    