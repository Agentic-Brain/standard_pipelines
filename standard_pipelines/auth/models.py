from sqlalchemy import DateTime, func, String, Integer, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, relationship, mapped_column, declared_attr
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError
from flask_security.core import UserMixin, RoleMixin
from standard_pipelines.extensions import db
from standard_pipelines.database.models import BaseMixin
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime, timezone
import uuid
from standard_pipelines.database.models import SecureMixin
from flask import current_app

if TYPE_CHECKING:
    from standard_pipelines.data_flow.models import Client

class Role(BaseMixin, RoleMixin):
    __tablename__ = 'role'
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str] = mapped_column(String(255))
    users: Mapped[list['User']] = relationship('User', secondary='user_role_join', back_populates='roles', passive_deletes=True)

    # TODO: init function

class User(BaseMixin, UserMixin):
    __tablename__ = 'user'
    # Default core usage info
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean)
    confirmed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime)

    # Add Custom fields here

    # Extra details Flask_Security Details
    fs_uniquifier: Mapped[str] = mapped_column(String(64), unique=True)
    
    # SECURITY_TRACKABLE requirements
    last_login_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    current_login_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    last_login_ip: Mapped[str] = mapped_column(String, server_default='0.0.0.0')
    current_login_ip: Mapped[str] = mapped_column(String, server_default='0.0.0.0')
    login_count: Mapped[int] = mapped_column(Integer, server_default='0')
    
    # SECURITY TWO FACTOR requirements
    tf_totp_secret: Mapped[Optional[str]] = mapped_column(String(255))
    tf_primary_method: Mapped[Optional[str]] = mapped_column(String)
    tf_phone_number: Mapped[Optional[str]] = mapped_column(String(128))

    # DataFlow Client relationship
    client_id: Mapped[UUID] = mapped_column(UUID, ForeignKey('client.id', ondelete='CASCADE'), nullable=False)
    client: Mapped['Client'] = relationship('Client', back_populates='users')
    
    # Role relationship
    roles: Mapped[list['Role']] = relationship('Role', secondary='user_role_join', back_populates='users', passive_deletes=True)

# Jointable
# TODO: setup cascsading delete to remove join entry if a user is deleted
# TODO: Change this to GUID, Will need to join on GUID as well
class UserRoleJoin(BaseMixin):
    __tablename__ = 'user_role_join'
    user_id: Mapped[UUID] = mapped_column(UUID, ForeignKey('user.id', ondelete='CASCADE')) 
    role_id: Mapped[UUID] = mapped_column(UUID, ForeignKey('role.id', ondelete='CASCADE'))

class BaseCredentials(SecureMixin):
    """Base model for storing encrypted credentials."""

    __abstract__ = True
    
    # Link to client for encryption key lookup
    client_id: Mapped[UUID] = mapped_column(
        UUID, 
        ForeignKey('client.id', ondelete='CASCADE'),
        unique=True
    )
    
    @declared_attr
    def client(self) -> Mapped['Client']:
        return relationship('Client')
    
    def get_encryption_key(self) -> bytes:
        """Get encryption key from Bitwarden using the client's encryption key ID."""
        
        # Get Bitwarden client from Flask app extensions
        
        bitwarden_client = current_app.extensions['bitwarden_client']
        
        # Retrieve the secret using the client's encryption key ID
        try:
            secret = bitwarden_client.secrets().get(self.client.bitwarden_encryption_key_id)
            if secret.success:
                return secret.data.value.encode()
            else:
                raise Exception(f"Failed to retrieve secret from Bitwarden: {secret.data.error}")
        except Exception as e:
            print(f"Error retrieving secret from Bitwarden: {e}")
            raise e
        

    def __repr__(self) -> str:
        """Return string representation showing client name and credential type."""
        return f"<{self.__class__.__name__} for {self.client.name}>"


class HubSpotCredentials(BaseCredentials):
    """Credentials for HubSpot API access."""
    __tablename__ = 'hubspot_credential'
    
    # Previously overshadowed the parent's client_id column -- rename it:
    hubspot_client_id: Mapped[str] = mapped_column(String(255))
    hubspot_client_secret: Mapped[str] = mapped_column(String(255))
    hubspot_refresh_token: Mapped[str] = mapped_column(String(255))
    
    def __init__(self, client_id: UUID, hubspot_client_id: str, hubspot_client_secret: str, hubspot_refresh_token: str):
        super().__init__(client_id=client_id)
        self.hubspot_client_id = hubspot_client_id
        self.hubspot_client_secret = hubspot_client_secret
        self.hubspot_refresh_token = hubspot_refresh_token


class FirefliesCredentials(BaseCredentials):
    """Credentials for Fireflies.ai API access."""
    __tablename__ = 'fireflies_credential'
    
    # API Key for Fireflies.ai
    fireflies_api_key: Mapped[str] = mapped_column(String(255))
    
    def __init__(self, client_id: UUID, fireflies_api_key: str):
        self.client_id = client_id
        self.fireflies_api_key = fireflies_api_key