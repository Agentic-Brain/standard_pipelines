from sqlalchemy import String, Text, Boolean, ForeignKey, Index, text, UUID
from typing import Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship, declared_attr
from standard_pipelines.database.models import BaseMixin, SecureMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from standard_pipelines.auth.models import User

class Notification(BaseMixin):
    """Model for storing notifications with title and body for consumption by apprise."""
    __tablename__ = 'notifications'
    
    uri: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def __repr__(self):
        return f'<Notification {self.title}>'

class Client(BaseMixin):
    __tablename__ = 'client'
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    bitwarden_encryption_key_id: Mapped[str] = mapped_column(String(255))
    
    # Relationships
    users: Mapped[List['User']] = relationship('User', back_populates='client', passive_deletes=True)
    data_flows: Mapped[List['DataFlow']] = relationship(
        'DataFlow',
        secondary='client_data_flow_join',
        back_populates='clients',
        passive_deletes=True,
    )
    
    def __repr__(self) -> str:
        return f"<Client {self.name}>"
 
class DataFlow(BaseMixin):
    """Registry of available transformers in the system"""
    __tablename__ = 'data_flow'
    
    # Basic information
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000))

    
    # Implementation details
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Relationships
    clients: Mapped[List['Client']] = relationship(
        'Client', 
        secondary='client_data_flow_join',
        back_populates='data_flows',
        passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<DataFlow {self.name} v{self.version}>"

class DataFlowConfiguration(BaseMixin):
    """Base class for data flow configurations"""
    __abstract__ = True
    
    @declared_attr
    def is_default(cls) -> Mapped[bool]:
        return mapped_column(Boolean, default=False, server_default='false')

    @declared_attr
    def client_id(cls) -> Mapped[UUID]:
        return mapped_column(
            UUID,
            ForeignKey('client.id', ondelete='CASCADE'),
            nullable=True,
            unique=True
        )

    @declared_attr
    def registry_id(cls) -> Mapped[UUID]:
        return mapped_column(
            UUID,
            ForeignKey('data_flow.id', ondelete='CASCADE'),
            nullable=False
        )

    @declared_attr
    def registry(cls) -> Mapped['DataFlow']:
        return relationship('DataFlow')

    @declared_attr
    def __table_args__(cls):
        return (
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
        )

class ClientDataFlowJoin(BaseMixin):
    """Join table for clients and data_flow"""
    __tablename__ = 'client_data_flow_join'
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    webhook_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    client_id: Mapped[UUID] = mapped_column(
        UUID, 
        ForeignKey('client.id', ondelete='CASCADE'),
        nullable=False
    )
    data_flow_id: Mapped[UUID] = mapped_column(
        UUID, 
        ForeignKey('data_flow.id', ondelete='CASCADE'),
        nullable=False
    )