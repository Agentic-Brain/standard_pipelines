from sqlalchemy import DateTime, String, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Dict, Any, List
from datetime import datetime
import enum
from flask_base.database.models import BaseMixin
from sqlalchemy.dialects.postgresql import JSONB
from dataclasses import dataclass
from flask import current_app
import json

class TransformerStatus(enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"
    DISABLED = "disabled"

class TransformerType(enum.Enum):
    ETL = "etl"
    WEBHOOK = "webhook"
    EMAIL = "email"
    API = "api"
    CUSTOM = "custom"

@dataclass
class TransformerResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

class TransformerMixin(BaseMixin):
    """Mixin for transformer models providing common pipeline functionality"""
    __abstract__ = True

    # Pipeline metadata
    transformer_type: Mapped[TransformerType] = mapped_column(
        Enum(TransformerType), 
        nullable=False, 
        default=TransformerType.CUSTOM
    )
    status: Mapped[TransformerStatus] = mapped_column(
        Enum(TransformerStatus), 
        nullable=False, 
        default=TransformerStatus.IDLE
    )
    
    # Scheduling and timing
    schedule: Mapped[Optional[str]] = mapped_column(String(100))  # Cron expression
    last_run_start: Mapped[Optional[DateTime]] = mapped_column(DateTime)
    last_run_end: Mapped[Optional[DateTime]] = mapped_column(DateTime)
    next_scheduled_run: Mapped[Optional[DateTime]] = mapped_column(DateTime)
    
    # Configuration and state
    input_schema: Mapped[Optional[Dict]] = mapped_column(JSONB)  # Expected input format
    output_schema: Mapped[Optional[Dict]] = mapped_column(JSONB)  # Expected output format
    config: Mapped[Dict] = mapped_column(JSONB, default={})  # Transformer-specific configuration
    state: Mapped[Dict] = mapped_column(JSONB, default={})  # Persistent state between runs
    
    # Error handling and logging
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    retry_delay: Mapped[int] = mapped_column(Integer, default=300)  # seconds
    error_log: Mapped[List[Dict]] = mapped_column(JSONB, default=[])

    def start_run(self) -> None:
        """Mark transformer as running and record start time"""
        try:
            self.status = TransformerStatus.RUNNING
            self.last_run_start = datetime.utcnow()
            self.save()
        except Exception as e:
            current_app.logger.error(f"Failed to start transformer run: {str(e)}")
            raise

    def end_run(self, success: bool, message: str, data: Optional[Dict] = None) -> None:
        """Record end of run with status and results"""
        try:
            self.last_run_end = datetime.utcnow()
            self.status = TransformerStatus.COMPLETED if success else TransformerStatus.FAILED
            
            if not success:
                self._log_error(message, data)
            
            self.save()
        except Exception as e:
            current_app.logger.error(f"Failed to end transformer run: {str(e)}")
            raise

    def _log_error(self, message: str, data: Optional[Dict] = None) -> None:
        """Add error to error log"""
        error_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "data": data
        }
        self.error_log.append(error_entry)
        if len(self.error_log) > 100:  # Keep last 100 errors
            self.error_log = self.error_log[-100:]

    def validate_input(self, input_data: Dict) -> bool:
        """Validate input data against schema if defined"""
        if not self.input_schema:
            return True
        try:
            # TODO: Implement schema validation
            # Could use jsonschema or similar library
            return True
        except Exception as e:
            current_app.logger.error(f"Input validation failed: {str(e)}")
            return False

    def validate_output(self, output_data: Dict) -> bool:
        """Validate output data against schema if defined"""
        if not self.output_schema:
            return True
        try:
            # TODO: Implement schema validation
            return True
        except Exception as e:
            current_app.logger.error(f"Output validation failed: {str(e)}")
            return False

    def update_state(self, new_state: Dict) -> None:
        """Update transformer state"""
        try:
            self.state.update(new_state)
            self.save()
        except Exception as e:
            current_app.logger.error(f"Failed to update state: {str(e)}")
            raise

    def should_retry(self) -> bool:
        """Determine if transformer should retry based on error log"""
        recent_errors = [
            error for error in self.error_log 
            if (datetime.utcnow() - datetime.fromisoformat(error["timestamp"])).total_seconds() < self.retry_delay
        ]
        return len(recent_errors) < self.max_retries

    @property
    def is_running(self) -> bool:
        return self.status == TransformerStatus.RUNNING

    @property
    def is_failed(self) -> bool:
        return self.status == TransformerStatus.FAILED

    @property
    def run_duration(self) -> Optional[float]:
        """Calculate last run duration in seconds"""
        if self.last_run_start and self.last_run_end:
            return (self.last_run_end - self.last_run_start).total_seconds()
        return None 