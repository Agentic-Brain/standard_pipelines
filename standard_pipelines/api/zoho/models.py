from sqlalchemy import String, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property

from standard_pipelines.api.oauth_system import OAuthCredentialMixin, OAuthConfig
from standard_pipelines.database.models import unencrypted_mapped_column


class ZohoCredentials(OAuthCredentialMixin):
    """Credentials for Zoho API access."""
    __tablename__ = 'zoho_credential'
    __abstract__ = False  # This is a concrete implementation

    # Zoho stores client credentials separately (legacy support)
    oauth_client_id: Mapped[str] = mapped_column(String(255))
    oauth_client_secret: Mapped[str] = mapped_column(String(255))
    
    # Legacy field for expires_at (unencrypted as before)
    oauth_expires_at: Mapped[int] = unencrypted_mapped_column(Integer)
    
    # Backward compatibility properties for old field names
    @hybrid_property
    def oauth_refresh_token(self):
        """Override parent to maintain field name compatibility."""
        return super().oauth_refresh_token
    
    @oauth_refresh_token.setter
    def oauth_refresh_token(self, value):
        """Override parent to maintain field name compatibility."""
        # Call parent setter through property
        OAuthCredentialMixin.oauth_refresh_token.fset(self, value)
    
    @hybrid_property
    def oauth_access_token(self):
        """Override parent to maintain field name compatibility."""
        return super().oauth_access_token
    
    @oauth_access_token.setter
    def oauth_access_token(self, value):
        """Override parent to maintain field name compatibility."""
        # Call parent setter through property
        OAuthCredentialMixin.oauth_access_token.fset(self, value)
        
    def __init__(self, client_id: UUID, oauth_client_id: str = '', oauth_client_secret: str = '', **kwargs):
        self.client_id = client_id
        self.oauth_client_id = oauth_client_id
        self.oauth_client_secret = oauth_client_secret
        super().__init__(**kwargs)
    
    @classmethod
    def get_oauth_config(cls) -> OAuthConfig:
        return OAuthConfig(
            name='zoho',
            display_name='Zoho',
            client_id_env='ZOHO_CLIENT_ID',
            client_secret_env='ZOHO_CLIENT_SECRET',
            authorize_url='https://accounts.zoho.com/oauth/v2/auth',
            access_token_url='https://accounts.zoho.com/oauth/v2/token',
            api_base_url='https://www.zohoapis.com/',
            scopes=[
                'ZohoCRM.users.ALL',
                'ZohoCRM.settings.ALL',
                'ZohoCRM.modules.ALL',
                'ZohoSearch.securesearch.READ',
                'ZohoCRM.org.ALL'
            ],
            icon_path='img/oauth/zoho.svg',
            description='Connect to Zoho to sync contacts and deals'
        )
    
    @classmethod
    def from_oauth_callback(cls, client_id, token, user_info=None):
        """Override to store client credentials from config."""
        from flask import current_app
        
        instance = super().from_oauth_callback(client_id, token, user_info)
        
        # Store the OAuth app's credentials (not user-specific)
        config = cls.get_oauth_config()
        instance.oauth_client_id = current_app.config.get(config.client_id_env, '')
        instance.oauth_client_secret = current_app.config.get(config.client_secret_env, '')
        
        # Handle expires_at
        if token.get('expires_at'):
            instance.oauth_expires_at = token['expires_at']
            instance.oauth_token_expires_at = token['expires_at']
        
        return instance