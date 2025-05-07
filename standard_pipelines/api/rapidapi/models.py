from standard_pipelines.auth.models import BaseCredentials
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class RapidAPICredentials(BaseCredentials):
    """Credentials for RapidAPI services."""
    __tablename__ = 'rapidapi_credential'

    rapidapi_key: Mapped[str] = mapped_column(Text)
    rapidapi_host: Mapped[str] = mapped_column(Text)

    def __init__(self, client_id: UUID, rapidapi_key: str, rapidapi_host: str):
        self.client_id = client_id
        self.rapidapi_key = rapidapi_key
        self.rapidapi_host = rapidapi_host