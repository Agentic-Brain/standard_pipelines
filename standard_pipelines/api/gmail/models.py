from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from standard_pipelines.auth.models import BaseCredentials

class GmailCredentials(BaseCredentials):
    """Credentials for Gmail API access."""
    __tablename__ = 'gmail_credential'
    
    access_token: Mapped[str] = mapped_column(String(255))
    refresh_token: Mapped[str] = mapped_column(String(255))
        
    def __init__(self, access_token: str, refresh_token: str):
        self.access_token = access_token
        self.refresh_token = refresh_token