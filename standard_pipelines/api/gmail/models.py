from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import uuid
from standard_pipelines.database.models import BaseCredentials

class GmailCredentials(BaseCredentials):
    """Credentials for Gmail API access."""
    __tablename__ = 'gmail_credentials'
    
    # Unique identifier for the credentials
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'), nullable=False)

    access_token: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(255), nullable=True)
    token_uri: Mapped[str] = mapped_column(String(255), nullable=False)
    
    oauth_client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    oauth_client_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    
    scopes: Mapped[str] = mapped_column(String(255), nullable=False)
    
    updated_at: Mapped[DateTime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __init__(self, user_id: int, access_token: str, refresh_token: str, token_uri: str, oauth_client_id: str, oauth_client_secret: str, scopes: str):
        self.user_id = user_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_uri = token_uri
        self.oauth_client_id = oauth_client_id
        self.oauth_client_secret = oauth_client_secret
        self.scopes = scopes