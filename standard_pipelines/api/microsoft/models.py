from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from standard_pipelines.auth.models import BaseCredentials
from standard_pipelines.database.models import unencrypted_mapped_column


class MicrosoftCredentials(BaseCredentials):
    """Credentials for Microsoft API access."""
    __tablename__ = 'microsoft_credential'

    # Override table args to remove unique constraint on client_id
    __table_args__ = ()

    access_token: Mapped[str] = mapped_column(String(4000))
    refresh_token: Mapped[str] = mapped_column(String(4000))
    expires_at: Mapped[int] = unencrypted_mapped_column(Integer)
    user_email: Mapped[str] = mapped_column(String(511))
    user_name: Mapped[Optional[str]] = mapped_column(String(511))

    def __init__(self, client_id: UUID, access_token: str, refresh_token: str, expires_at: int, user_email: str, user_name: str):
        super().__init__(client_id=client_id) # type: ignore
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at
        self.user_email = user_email
        self.user_name = user_name

#uv run flask db downgrade
#uv run flask db migrate -m "add microsoft oauth table"
#uv run flask db upgrade