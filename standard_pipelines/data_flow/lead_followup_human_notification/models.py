from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from ..models import DataFlowConfiguration

class LeadFollowupHumanNotificationConfiguration(DataFlowConfiguration):
    # Name shortened to config to prevent 63 character limit
    __tablename__ = 'lead_followup_human_notification_config'
    
    # Email to send from (Gmail user's email address)
    fallback_destination_email: Mapped[str] = mapped_column(String(255))
    source_email: Mapped[str] = mapped_column(String(255))