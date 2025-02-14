from sqlalchemy import Text, Integer
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from ..models import DataFlowConfiguration

class GmailIntervalFollowupConfiguration(DataFlowConfiguration):
    __tablename__ = 'gmail_interval_followup_configuration'

    prompt: Mapped[str] = mapped_column(Text, nullable=True)
    email_interval_days: Mapped[int] = mapped_column(Integer, default=7)
    email_retries: Mapped[int] = mapped_column(Integer, default=3)
    email_body_prompt: Mapped[str] = mapped_column(Text)
    subject_line_template: Mapped[str] = mapped_column(Text)
    
