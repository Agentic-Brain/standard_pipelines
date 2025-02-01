from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone, timedelta
from standard_pipelines.auth.models import BaseCredentials
from flask import current_app

class GmailCredentials(BaseCredentials):
    """Credentials for Gmail API access."""
    __tablename__ = 'gmail_credential'
    
    access_token: Mapped[str] = mapped_column(String(255), nullable=False)
    expire_time: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(255), nullable=False)
        
    def __init__(self, access_token: str, expire_time: str, refresh_token: str):
        self.access_token = access_token
        self.expire_time = expire_time
        self.refresh_token = refresh_token

    def set_expire_time_from_datetime(self, expire_time: datetime):
        """Set expire_time from a datetime object."""
        try:
            self.expire_time = expire_time.isoformat() 
        except Exception as e:
            current_app.logger.warning(f"Error setting expire_time: {str(e)}")
            self.expire_time = datetime.now(timezone.utc) + timedelta(minutes=55) #Sets a default time

    def get_expire_time_as_datetime(self) -> datetime:
        """Convert expire_time string back to datetime."""
        try:
            return datetime.fromisoformat(self.expire_time)
        except Exception as e:
            current_app.logger.warning(f"Error converting expire_time to datetime: {str(e)}")
            return datetime.now(timezone.utc) - timedelta(minutes=5) #Force a refresh