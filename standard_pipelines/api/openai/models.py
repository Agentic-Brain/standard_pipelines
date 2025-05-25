from standard_pipelines.auth.models import BaseCredentials


from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class OpenAICredentials(BaseCredentials):
    """Credentials for OpenAI API access."""
    __tablename__ = 'openai_credential'

    # API Key for OpenAI
    openai_api_key: Mapped[str] = mapped_column(Text)

    def __init__(self, client_id: UUID, openai_api_key: str, **kwargs):
        self.client_id = client_id
        self.openai_api_key = openai_api_key
        super().__init__(**kwargs)