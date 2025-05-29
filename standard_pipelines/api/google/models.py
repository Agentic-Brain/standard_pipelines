from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Dict, Any
from sqlalchemy.ext.hybrid import hybrid_property

from standard_pipelines.api.oauth_system import OAuthCredentialMixin, OAuthConfig


class GoogleCredentials(OAuthCredentialMixin):
    """Credentials for Google API access."""
    __tablename__ = 'google_credential'
    __abstract__ = False  # This is a concrete implementation
    
    # Override table args to remove unique constraint on client_id
    __table_args__ = ()

    # Google-specific fields
    user_email: Mapped[str] = mapped_column(String(255))
    user_name: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Backward compatibility property
    @hybrid_property
    def refresh_token(self):
        """Backward compatibility for old field name."""
        return self.oauth_refresh_token
    
    @refresh_token.setter
    def refresh_token(self, value):
        """Backward compatibility for old field name."""
        self.oauth_refresh_token = value
    
    def __init__(self, client_id: UUID, refresh_token: str = None, user_email: str = None, user_name: str = None, **kwargs):
        self.client_id = client_id
        if refresh_token:
            self.oauth_refresh_token = refresh_token
        if user_email:
            self.user_email = user_email
        if user_name:
            self.user_name = user_name
        super().__init__(**kwargs)
    
    @classmethod
    def get_oauth_config(cls) -> OAuthConfig:
        return OAuthConfig(
            name='google',
            display_name='Google',
            client_id_env='GOOGLE_CLIENT_ID',
            client_secret_env='GOOGLE_CLIENT_SECRET',
            authorize_url='https://accounts.google.com/o/oauth2/auth',
            access_token_url='https://oauth2.googleapis.com/token',
            api_base_url='https://www.googleapis.com/',
            scopes=[
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.compose',
                'https://www.googleapis.com/auth/gmail.insert',
                'https://www.googleapis.com/auth/gmail.labels',
                'https://www.googleapis.com/auth/gmail.metadata',
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/gmail.settings.basic',
                'https://www.googleapis.com/auth/gmail.settings.sharing'
            ],
            icon_path='img/oauth/google.svg',
            description='Connect to Google for email integration',
            user_info_endpoint='https://www.googleapis.com/oauth2/v3/userinfo',
            user_info_fields={
                'user_email': 'email',
                'user_name': 'name'
            },
            extra_authorize_params={
                'access_type': 'offline',
                'prompt': 'consent'
            }
        )