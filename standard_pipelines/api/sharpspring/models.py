from standard_pipelines.auth.models import BaseCredentials
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class SharpSpringCredentials(BaseCredentials):
    """Credentials for SharpSpring API access."""
    __tablename__ = 'sharpspring_credential'

    account_id: Mapped[str] = mapped_column(String(255))
    secret_key: Mapped[str] = mapped_column(String(255))

    def __init__(self, client_id: UUID, account_id: str, secret_key: str, **kwargs):
        self.client_id = client_id
        self.account_id = account_id
        self.secret_key = secret_key
        super().__init__(**kwargs)