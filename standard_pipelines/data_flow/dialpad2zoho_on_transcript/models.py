from sqlalchemy import String, Text, Boolean, ForeignKey, Index, text, UUID
from typing import Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..models import DataFlowConfiguration

class Dialpad2ZohoOnTranscriptConfiguration(DataFlowConfiguration):
    __tablename__ = 'dialpad2zoho_on_transcript_configuration'

    prompt: Mapped[str] = mapped_column(Text, nullable=True)
    # Kept for backward compatibility but no longer used
    initial_deal_stage_id: Mapped[str] = mapped_column(String(255), nullable=True)
    email_domain: Mapped[str] = mapped_column(String(255))
    
