from sqlalchemy import String, Text, Boolean, ForeignKey, Index, text, UUID
from typing import Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..models import DataFlowConfiguration

class AddDataToHubspotFieldConfiguration(DataFlowConfiguration):
    __tablename__ = 'add_data_to_hubspot_field_configuration'

    # No additional configuration needed for this data flow
