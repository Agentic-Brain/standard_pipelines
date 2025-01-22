from sqlalchemy import String, Text, Boolean, ForeignKey, Index, text, UUID
from typing import Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from standard_pipelines.database.models import BaseMixin
from standard_pipelines.auth.models import Client

class Notification(BaseMixin):
    """Model for storing notifications with title and body for consumption by apprise."""
    __tablename__ = 'notifications'
    
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def __repr__(self):
        return f'<Notification {self.title}>'
    
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
    client_id: Mapped[UUID] = mapped_column(
        UUID, 
        ForeignKey('client.id', ondelete='CASCADE'),
        nullable=True,
        unique=True
    )
    
    # Link to registry
    registry_id: Mapped[UUID] = mapped_column(
        UUID, 
        ForeignKey('data_flow_registry.id', ondelete='CASCADE'),
        nullable=False
    )
    
    registry: Mapped['DataFlowRegistry'] = relationship('DataFlowRegistry')
    __table_args__ = (
        # There may only be a single row where is_default is true
        Index(
            'ix_unique_default_config',
            'registry_id',
            'is_default',
            unique=True,
            postgresql_where=text('is_default = true')
        ),
        # There may only be a single row where client_id is null
        Index(
            'ix_unique_client_id_config',
            'registry_id',
            'client_id',
            unique=True,
            postgresql_where=text('client_id IS NULL')
        ),
        # TODO: the row where client_id is null must be the default row
    )

class ClientDataFlowRegistryJoin(BaseMixin):
    """Join table for clients and data_flow registry"""
    __tablename__ = 'client_data_flow_registry_join'
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    webhook_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
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