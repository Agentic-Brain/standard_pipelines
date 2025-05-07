from sqlalchemy import String, Text, Boolean, ForeignKey, Index, text, UUID
from typing import Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..models import DataFlowConfiguration

# REMOVE: UNUSED
class AppendHubspotNoteConfiguration(DataFlowConfiguration):
    __tablename__ = 'append_hubspot_note_configuration'

    # No additional configuration needed for this data flow
