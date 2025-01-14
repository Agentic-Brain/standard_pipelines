from sqlalchemy import DateTime, String, Integer, Boolean, ForeignKey, Enum, inspect, and_, Index, text
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from standard_pipelines.database.models import BaseMixin
from standard_pipelines.auth.models import Client
from typing import Optional, List, Dict, Any
import datetime
import enum
import json
from standard_pipelines.extensions import db

class TransformerActivationType(enum.Enum):
    MANUAL = "manual"
    WEBHOOK = "webhook"
    POLLING = "polling"
    TRIGGER = "trigger"
    CUSTOM = "custom"

class TransformerTargetType(enum.Enum):
    EMAIL = "email"
    CRM = "crm"
    CALENDER = "calendar"
    CUSTOM = "custom"
    
class TransformerRegistry(BaseMixin):
    """Registry of available transformers in the system"""
    __tablename__ = 'transformer_registry'
    
    # Basic information
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    activation_type: Mapped[TransformerActivationType] = mapped_column(
        Enum(TransformerActivationType), 
        nullable=False,
        default=TransformerActivationType.CUSTOM
    )
    target_type: Mapped[TransformerTargetType] = mapped_column(
        Enum(TransformerTargetType), 
        nullable=False,
        default=TransformerTargetType.CUSTOM
    )
    
    # Implementation details
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Default configuration schema
    default_config: Mapped[Dict] = mapped_column(JSONB, default={})
    
    # Relationships
    clients: Mapped[List['Client']] = relationship(
        'Client', 
        secondary='client_transformer_join',
        back_populates='transformers',
        passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<TransformerRegistry {self.name} v{self.version}>"
    
class TransformerConfigurationMixin(BaseMixin):
    """Base mixin for transformer implementations"""
    __abstract__ = True
    
    # Runtime configuration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    
    # Execution tracking
    last_run: Mapped[Optional[DateTime]] = mapped_column(DateTime)
    run_count: Mapped[int] = mapped_column(Integer, default=0, server_default='0')
    
    # Link to registry
    registry_id: Mapped[UUID] = mapped_column(
        UUID, 
        ForeignKey('transformer_registry.id', ondelete='CASCADE'),
        nullable=False
    )
    registry: Mapped['TransformerRegistry'] = relationship('TransformerRegistry')
    
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

class ClientTransformerRegistryJoin(BaseMixin):
    """Join table for clients and transformer registry"""
    __tablename__ = 'client_transformer_registry_join'
    
    client_id: Mapped[UUID] = mapped_column(
        UUID, 
        ForeignKey('client.id', ondelete='CASCADE'),
        nullable=False
    )
    transformer_id: Mapped[UUID] = mapped_column(
        UUID, 
        ForeignKey('transformer_registry.id', ondelete='CASCADE'),
        nullable=False
    ) 

class TransformerRunStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TransformerRun(BaseMixin):
    """Records individual transformer execution instances"""
    __tablename__ = 'transformer_run'
    
    # Execution metadata
    started_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime)
    status: Mapped[TransformerRunStatus] = mapped_column(
        Enum(TransformerRunStatus),
        nullable=False,
        default=TransformerRunStatus.PENDING
    )
        
    # Relationships
    client_id: Mapped[UUID] = mapped_column(
        UUID,
        ForeignKey('client.id', ondelete='CASCADE'),
        nullable=False
    )
    client: Mapped['Client'] = relationship('Client')
    
    registry_id: Mapped[UUID] = mapped_column(
        UUID,
        ForeignKey('transformer_registry.id', ondelete='CASCADE'),
        nullable=False
    )
    registry: Mapped['TransformerRegistry'] = relationship('TransformerRegistry')
    
    def __repr__(self) -> str:
        return f"<TransformerRun {self.registry.name} ({self.status.value}) {self.started_at}>"
    
    # @property
    # def duration(self) -> Optional[float]:
    #     """Get run duration in seconds"""
    #     if self.completed_at is not None:
    #         return (self.completed_at - self.started_at).total_seconds()
    #     return None
    
    def start(self) -> None:
        """Mark run as started"""
        self.status = TransformerRunStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.save()
    
    def complete(self, output_data: Optional[Dict] = None) -> None:
        """Mark run as completed"""
        self.status = TransformerRunStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if output_data:
            self.output_data = output_data
        self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.save()
    
    def fail(self, error_message: str) -> None:
        """Mark run as failed"""
        self.status = TransformerRunStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.save()
    

    @classmethod
    def get_client_runs(cls, 
                       client_id: UUID, 
                       status: Optional[TransformerRunStatus] = None,
                       limit: int = 100) -> List['TransformerRun']:
        """Get transformer runs for a specific client"""
        query = db.session.query(cls).filter(cls.client_id == client_id)
        if status:
            query = query.filter(cls.status == status)
        return query.order_by(cls.started_at.desc()).limit(limit).all() 