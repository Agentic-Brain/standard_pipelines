from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from standard_pipelines.auth.models import BaseCredentials
from typing import Optional

class DialpadCredentials(BaseCredentials):
    """Credentials for Dialpad API access."""
    __tablename__ = 'dialpad_credential'

    # API Key for Dialpad
    dialpad_api_key: Mapped[str] = mapped_column(String(255))
    dialpad_jwt_secret: Mapped[Optional[str]] = mapped_column(String(255))

    # TODO: Consider breaking dialpad credentials and dialpad jwt secret into separate tables
    def __init__(self, client_id: UUID, dialpad_api_key: str, dialpad_jwt_secret: str, **kwargs):
        self.client_id = client_id
        self.dialpad_api_key = dialpad_api_key
        self.dialpad_jwt_secret = dialpad_jwt_secret
        super().__init__(**kwargs)
