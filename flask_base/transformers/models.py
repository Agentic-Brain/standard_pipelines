from sqlalchemy import DateTime, String, Integer, Boolean, ForeignKey, Enum, inspect, and_, Index, text, func
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from flask_base.database.models import BaseMixin
from flask_base.auth.models import Client
from typing import Optional, List, Dict, Any
import datetime
import enum
import json
from flask_base.extensions import db


    
class DataFlowRegistry(BaseMixin):
    """Registry of available transformers in the system"""
    __tablename__ = 'data_flow_registry'
    
    # Basic information
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000))

    
    # Implementation details
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Relationships
    clients: Mapped[List['Client']] = relationship(
        'Client', 
        secondary='client_data_flow_registry_join',
        back_populates='data_flows',
        passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<DataFlowRegistry {self.name} v{self.version}>"
    
class DataFlowConfigurationMixin(BaseMixin):
    """Base mixin for transformer implementations"""
    __abstract__ = True
    
    # Runtime configuration
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    
    # Link to registry
    registry_id: Mapped[UUID] = mapped_column(
        UUID, 
        ForeignKey('data_flow_registry.id', ondelete='CASCADE'),
        nullable=False
    )
    
    registry: Mapped['DataFlowRegistry'] = relationship('DataFlowRegistry')
    # Add a partial unique index for is_default
    __table_args__ = (
        Index(
            'ix_unique_default_config',
            'registry_id',
            'is_default',
            unique=True,
            postgresql_where=text('is_default = true')
        ),
    )

class ClientDataFlowRegistryJoin(BaseMixin):
    """Join table for clients and data_flow registry"""
    __tablename__ = 'client_data_flow_registry_join'
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    
    client_id: Mapped[UUID] = mapped_column(
        UUID, 
        ForeignKey('client.id', ondelete='CASCADE'),
        nullable=False
    )
    data_flow_id: Mapped[UUID] = mapped_column(
        UUID, 
        ForeignKey('data_flow_registry.id', ondelete='CASCADE'),
        nullable=False
    ) 
