from standard_pipelines.auth.models import BaseCredentials


from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from standard_pipelines.database.models import unencrypted_mapped_column


class ZohoCredentials(BaseCredentials):
    """Credentials for Zoho API access."""
    __tablename__ = 'zoho_credential'

    # Previously overshadowed the parent's client_id column -- rename it:
    oauth_client_id: Mapped[str] = mapped_column(String(255))
    oauth_client_secret: Mapped[str] = mapped_column(String(255))
    oauth_refresh_token: Mapped[str] = mapped_column(String(255))
    oauth_access_token: Mapped[str] = mapped_column(String(255))

    oauth_expires_at: Mapped[int] = unencrypted_mapped_column(Integer)

    def __init__(self, client_id: UUID, oauth_client_id: str, oauth_client_secret: str, **kwargs):
        self.client_id = client_id
        self.oauth_client_id = oauth_client_id
        self.oauth_client_secret = oauth_client_secret
        super().__init__(**kwargs)