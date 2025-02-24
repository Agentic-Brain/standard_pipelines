from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column
from ..models import DataFlowConfiguration



class DP2SSOnTranscriptConfiguration(DataFlowConfiguration):
    __tablename__ = 'dp2ss_on_transcript_configuration'

    prompt: Mapped[str] = mapped_column(Text, nullable=True)


