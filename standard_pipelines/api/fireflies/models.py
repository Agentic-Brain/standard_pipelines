from standard_pipelines.auth.models import BaseCredentials


from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class FirefliesCredentials(BaseCredentials):
    """Credentials for Fireflies.ai API access."""
    __tablename__ = 'fireflies_credential'

    # API Key for Fireflies.ai
    fireflies_api_key: Mapped[str] = mapped_column(String(255))

    def __init__(self, client_id: UUID, fireflies_api_key: str, **kwargs):
        self.client_id = client_id
        self.fireflies_api_key = fireflies_api_key
        super().__init__(**kwargs)