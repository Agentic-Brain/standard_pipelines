from sqlalchemy import DateTime, func, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError
from flask_security.core import UserMixin, RoleMixin
from standard_pipelines.extensions import db
from standard_pipelines.database.models import BaseMixin
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime, timezone
import uuid

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