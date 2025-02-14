from standard_pipelines.auth.models import BaseCredentials


from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

class GoogleCredentials(BaseCredentials):
    """Credentials for Google API access."""
    __tablename__ = 'google_credential'

    refresh_token: Mapped[str] = mapped_column(String(255))
    user_email: Mapped[str] = mapped_column(String(255))
    user_name: Mapped[Optional[str]] = mapped_column(String(255))
    def __init__(self, client_id: UUID, refresh_token: str, user_email: str, user_name: str):
        super().__init__(client_id=client_id)
        self.refresh_token = refresh_token
        self.user_email = user_email
        self.user_name = user_name