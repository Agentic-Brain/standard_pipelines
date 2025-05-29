from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from sqlalchemy.ext.hybrid import hybrid_property

from standard_pipelines.api.oauth_system import OAuthCredentialMixin, OAuthConfig


class HubSpotCredentials(OAuthCredentialMixin):
    """Credentials for HubSpot API access."""
    __tablename__ = 'hubspot_credential'
    __abstract__ = False  # This is a concrete implementation
    
    # HubSpot stores client credentials separately (legacy support)
    hubspot_client_id: Mapped[str] = mapped_column(String(255))
    hubspot_client_secret: Mapped[str] = mapped_column(String(255))
    
    # Backward compatibility property
    @hybrid_property
    def hubspot_refresh_token(self):
        """Backward compatibility for old field name."""
        return self.oauth_refresh_token
    
    @hubspot_refresh_token.setter
    def hubspot_refresh_token(self, value):
        """Backward compatibility for old field name."""
        self.oauth_refresh_token = value
    
    def __init__(self, client_id: UUID, hubspot_client_id: str = '', hubspot_client_secret: str = '', hubspot_refresh_token: str = None, **kwargs):
        self.client_id = client_id
        self.hubspot_client_id = hubspot_client_id
        self.hubspot_client_secret = hubspot_client_secret
        if hubspot_refresh_token:
            self.oauth_refresh_token = hubspot_refresh_token
        super().__init__(**kwargs)
    
    @classmethod
    def get_oauth_config(cls) -> OAuthConfig:
        return OAuthConfig(
            name='hubspot',
            display_name='HubSpot',
            client_id_env='HUBSPOT_CLIENT_ID',
            client_secret_env='HUBSPOT_CLIENT_SECRET',
            authorize_url='https://app.hubspot.com/oauth/authorize',
            access_token_url='https://api.hubapi.com/oauth/v1/token',
            api_base_url='https://api.hubapi.com/',
            scopes=[
                'crm.objects.contacts.read',
                'crm.objects.contacts.write',
                'crm.objects.deals.read',
                'crm.objects.deals.write',
                'crm.schemas.deals.read',
                'crm.schemas.deals.write',
                'oauth',
                'crm.objects.users.read',
                'crm.objects.users.write'
            ],
            icon_path='img/oauth/hubspot.svg',
            description='Connect to HubSpot to sync contacts and deals'
        )
    
    @classmethod
    def from_oauth_callback(cls, client_id, token, user_info=None):
        """Override to store client credentials from config."""
        from flask import current_app
        
        instance = super().from_oauth_callback(client_id, token, user_info)
        
        # Store the OAuth app's credentials (not user-specific)
        config = cls.get_oauth_config()
        instance.hubspot_client_id = current_app.config.get(config.client_id_env, '')
        instance.hubspot_client_secret = current_app.config.get(config.client_secret_env, '')
        
        return instance