from sqlalchemy import String, Text, ForeignKey, JSON
from typing import Optional, Dict, Any
from sqlalchemy.orm import Mapped, mapped_column
from ..models import DataFlowConfiguration


class DeepResearchConfiguration(DataFlowConfiguration):
    """Configuration for Deep Research flow that analyzes LinkedIn profiles for HubSpot."""
    __tablename__ = 'deep_research_configuration'
    
    # HubSpot configuration
    hubspot_record_type: Mapped[str] = mapped_column(String(50), default="contact")
    
    # LinkedIn analysis settings
    openai_model: Mapped[str] = mapped_column(String(100), default="o1-preview-2024-09-12")
    
    # Mapping of HubSpot properties to LinkedIn data fields (stored as JSON)
    properties_mapping: Mapped[Dict[str, Any]] = mapped_column(JSON, default={})