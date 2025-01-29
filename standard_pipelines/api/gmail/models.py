from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from standard_pipelines.auth.models import BaseCredentials

class GmailCredentials(BaseCredentials):
    """Credentials for Gmail API access."""
    __tablename__ = 'gmail_credential'
    
    access_token: Mapped[str] = mapped_column(String(255), nullable=False)
    expire_time: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(255), nullable=False)
    token_uri: Mapped[str] = mapped_column(String(255), nullable=False)
    

    oauth_client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    oauth_client_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    
    scopes: Mapped[str] = mapped_column(String(255), nullable=False)
        
    def __init__(self, access_token: str, expire_time: str, refresh_token: str, token_uri: str, oauth_client_id: str, oauth_client_secret: str, scopes: str):
        self.access_token = access_token
        self.expire_time = expire_time
        self.refresh_token = refresh_token
        self.token_uri = token_uri
        self.oauth_client_id = oauth_client_id
        self.oauth_client_secret = oauth_client_secret
        self.scopes = scopes

    def set_expire_time_from_datetime(self, expire_time: datetime):
        """Set expire_time from a datetime object."""
        self.expire_time = expire_time.isoformat() if expire_time else None 

    def get_expire_time_as_datetime(self) -> datetime:
        """Convert expire_time string back to datetime."""
        return datetime.fromisoformat(self.expire_time) if self.expire_time else None