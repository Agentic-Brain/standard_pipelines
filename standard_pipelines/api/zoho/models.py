from standard_pipelines.auth.models import BaseCredentials


from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class ZohoCredentials(BaseCredentials):
    """Credentials for Zoho API access."""
    __tablename__ = 'zoho_credential'

    # Previously overshadowed the parent's client_id column -- rename it:
    zoho_client_id: Mapped[str] = mapped_column(String(255))
    zoho_client_secret: Mapped[str] = mapped_column(String(255))
    zoho_refresh_token: Mapped[str] = mapped_column(String(255))

    def __init__(self, client_id: UUID, zoho_client_id: str, zoho_client_secret: str, zoho_refresh_token: str):
        super().__init__(client_id=client_id)
        self.zoho_client_id = zoho_client_id
        self.zoho_client_secret = zoho_client_secret
        self.zoho_refresh_token = zoho_refresh_token