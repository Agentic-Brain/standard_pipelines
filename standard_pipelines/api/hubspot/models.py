from standard_pipelines.auth.models import BaseCredentials


from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class HubSpotCredentials(BaseCredentials):
    """Credentials for HubSpot API access."""
    __tablename__ = 'hubspot_credential'

    # Previously overshadowed the parent's client_id column -- rename it:
    hubspot_client_id: Mapped[str] = mapped_column(String(255))
    hubspot_client_secret: Mapped[str] = mapped_column(String(255))
    hubspot_refresh_token: Mapped[str] = mapped_column(String(255))

    def __init__(self, client_id: UUID, hubspot_client_id: str, hubspot_client_secret: str, hubspot_refresh_token: str):
        super().__init__(client_id=client_id)
        self.hubspot_client_id = hubspot_client_id
        self.hubspot_client_secret = hubspot_client_secret
        self.hubspot_refresh_token = hubspot_refresh_token