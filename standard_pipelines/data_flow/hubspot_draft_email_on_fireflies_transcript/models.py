from sqlalchemy import String, Text, Boolean, ForeignKey, Index, text, UUID
from typing import Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..models import DataFlowConfigurationMixin

class HubSpotDraftEmailOnFirefliesTranscriptConfiguration(DataFlowConfigurationMixin):
    __tablename__ = 'hubspot_draft_email_on_fireflies_transcript_configuration'

    hubspot_client_id_bitwarden_id: Mapped[str] = mapped_column(String(255), nullable=True)
    hubspot_client_secret_bitwarden_id: Mapped[str] = mapped_column(String(255), nullable=True)
    hubspot_refresh_token_bitwarden_id: Mapped[str] = mapped_column(String(255), nullable=True)
    fireflies_api_key_bitwarden_id: Mapped[str] = mapped_column(String(255), nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=True)
    

