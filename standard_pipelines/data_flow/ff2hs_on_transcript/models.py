from sqlalchemy import String, Text, Boolean, ForeignKey, Index, text, UUID
from typing import Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..models import DataFlowConfiguration

class FF2HSOnTranscriptConfiguration(DataFlowConfiguration):
    __tablename__ = 'ff2hs_on_transcript_configuration'

    prompt: Mapped[str] = mapped_column(Text, nullable=True)
    

