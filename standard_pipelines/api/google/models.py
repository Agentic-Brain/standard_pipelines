from standard_pipelines.auth.models import BaseCredentials


from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class GoogleCredentials(BaseCredentials):
    """Credentials for Google API access."""
    __tablename__ = 'google_credential'

    refresh_token: Mapped[str] = mapped_column(String(255))

    def __init__(self, client_id: UUID, refresh_token: str):
        super().__init__(client_id=client_id)
        self.refresh_token = refresh_token