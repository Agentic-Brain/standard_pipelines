from sqlalchemy import Text, Integer, String, ForeignKey, UUID
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from standard_pipelines.api.google.models import GoogleCredentials
from standard_pipelines.database.models import ScheduledMixin
from ..models import DataFlowConfiguration

class GmailIntervalFollowupConfiguration(DataFlowConfiguration):
    __tablename__ = 'gmail_interval_followup_configuration'

    prompt: Mapped[str] = mapped_column(Text, nullable=True)
    email_interval_days: Mapped[int] = mapped_column(Integer, default=7)
    email_retries: Mapped[int] = mapped_column(Integer, default=3)
    email_body_prompt: Mapped[str] = mapped_column(Text)
    subject_line_template: Mapped[str] = mapped_column(Text)
    internal_domain: Mapped[str] = mapped_column(String(255))
    
class GmailIntervalFollowupSchedule(ScheduledMixin):
    __tablename__ = 'gmail_interval_followup_schedule'
    configuration_id: Mapped[UUID] = mapped_column(ForeignKey('gmail_interval_followup_configuration.id'))
    thread_id: Mapped[UUID] = mapped_column(ForeignKey('gmail_thread.id'))
    gmail_credentials_id: Mapped[UUID] = mapped_column(ForeignKey('gmail_credentials.id'))
    configuration: Mapped[GmailIntervalFollowupConfiguration] = relationship()
    gmail_credentials: Mapped['GoogleCredentials'] = relationship()
