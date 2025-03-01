from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from standard_pipelines.auth.models import BaseCredentials


class FullEnrichCredentials(BaseCredentials):
    """Credentials for FullEnrich API access."""
    __tablename__ = 'fullenrich_credential'

    api_key: Mapped[str] = mapped_column(String(255))

    def __init__(self, client_id: UUID, api_key: str):
        super().__init__(client_id=client_id)
        self.api_key = api_key
