from standard_pipelines.auth.models import BaseCredentials
from sqlalchemy import String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from standard_pipelines.extensions import db

class GoogleCredentials(BaseCredentials):
    """Credentials for Google API access."""
    __tablename__ = 'google_credential'
    
    # Override table args to remove unique constraint on client_id
    __table_args__ = ()

    refresh_token: Mapped[str] = mapped_column(String(255))
    user_email: Mapped[str] = mapped_column(String(255))
    user_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def __init__(self, client_id: UUID, refresh_token: str, user_email: str, user_name: str, is_default: bool = False):
        super().__init__(client_id=client_id) # type: ignore
        self.refresh_token = refresh_token
        self.user_email = user_email
        self.user_name = user_name        self.is_default = is_default
        
    def save(self):
        if self.is_default:
            # Unset any existing defaults for this client
            existing_defaults = GoogleCredentials.query.filter_by(
                client_id=self.client_id, 
                is_default=True
            ).all()
            for cred in existing_defaults:
                if cred.id != self.id:  # Don't unset self if already in DB
                    cred.is_default = False
                    db.session.add(cred)
        db.session.add(self)
        db.session.commit()