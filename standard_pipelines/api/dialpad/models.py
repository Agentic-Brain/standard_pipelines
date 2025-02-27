from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from standard_pipelines.auth.models import BaseCredentials


class DialpadCredentials(BaseCredentials):
    """Credentials for Dialpad API access."""
    __tablename__ = 'dialpad_credential'

    # API Key for Dialpad
    dialpad_api_key: Mapped[str] = mapped_column(String(255))

    def __init__(self, client_id: UUID, dialpad_api_key: str):
        super().__init__(client_id=client_id)
        self.dialpad_api_key = dialpad_api_key
