"""
Office 365 OAuth credentials using the new OAuth system.
"""
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from standard_pipelines.database.models import unencrypted_mapped_column
from typing import Optional, Dict, Any

from standard_pipelines.api.oauth_system import OAuthCredentialMixin, OAuthConfig


class Office365Credentials(OAuthCredentialMixin):
    """Credentials for Office 365 API access."""
    __tablename__ = 'office365_credential'
    # TODO: Find some way to remove this requirement to add __abstract__ = False, lots of potential errors here
    __abstract__ = False  # This is a concrete implementation
    
    # Override table args to remove unique constraint on client_id
    # TODO: find a better way to handle these table args, most oauth are user specific, not client
    # TODO: Default should be duplicable, only a few should be a client only modification (maybe none)
    __table_args__ = ()

    # Office 365-specific fields
    user_email: Mapped[str] = unencrypted_mapped_column(String(255))
    user_name: Mapped[Optional[str]] = unencrypted_mapped_column(String(255))
    tenant_id: Mapped[Optional[str]] = unencrypted_mapped_column(String(255))
    user_principal_name: Mapped[Optional[str]] = unencrypted_mapped_column(String(255))
    
    def __init__(self, client_id: UUID, **kwargs):
        self.client_id = client_id
        super().__init__(**kwargs)
    
    @classmethod
    def get_oauth_config(cls) -> OAuthConfig:
        return OAuthConfig(
            name='office365',
            display_name='Microsoft Office 365',
            client_id_env='OFFICE365_CLIENT_ID',
            client_secret_env='OFFICE365_CLIENT_SECRET',
            authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
            access_token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token',
            api_base_url='https://graph.microsoft.com/v1.0/',
            scopes=[
                'https://graph.microsoft.com/User.Read',
                'https://graph.microsoft.com/Mail.Read',
                'https://graph.microsoft.com/Mail.Send',
                'https://graph.microsoft.com/Mail.ReadWrite',
                'https://graph.microsoft.com/Calendars.Read',
                'https://graph.microsoft.com/Calendars.ReadWrite',
                'https://graph.microsoft.com/Contacts.Read',
                'https://graph.microsoft.com/Contacts.ReadWrite',
                'https://graph.microsoft.com/Files.Read',
                'https://graph.microsoft.com/Files.ReadWrite'
            ],
            icon_path='img/oauth/office365.svg',
            description='Connect to Microsoft Office 365 for email, calendar, and file integration',
            user_info_endpoint='https://graph.microsoft.com/v1.0/me',
            user_info_fields={
                'user_email': 'userPrincipalName',
                'user_name': 'displayName'
            },
            extra_authorize_params={
                'response_type': 'code',
                'response_mode': 'query'
            }
        )
    
    @classmethod
    def from_oauth_callback(cls, client_id, token: Dict[str, Any], user_info: Optional[Dict[str, Any]] = None) -> 'Office365Credentials':
        """
        Create credential instance from OAuth callback data.
        Handle Office 365-specific user info mapping.
        """
        # Create instance directly instead of calling super() to ensure correct type
        instance = cls(client_id=client_id)
        instance.oauth_refresh_token = token.get('refresh_token', '')
        instance.oauth_access_token = token.get('access_token', '')
        instance.oauth_token_expires_at = token.get('expires_at')
        
        # Set Office 365-specific fields with fallbacks to ensure non-null values
        if user_info:
            instance.user_email = user_info.get('userPrincipalName') or user_info.get('mail') or 'unknown@domain.com'
            instance.user_name = user_info.get('displayName') or 'Unknown User'
            instance.tenant_id = user_info.get('tid') or 'unknown-tenant'
            instance.user_principal_name = user_info.get('userPrincipalName') or 'unknown@domain.com'
        else:
            # Fallback values if no user info provided
            instance.user_email = 'unknown@domain.com'
            instance.user_name = 'Unknown User'
            instance.tenant_id = 'unknown-tenant'
            instance.user_principal_name = 'unknown@domain.com'
        
        return instance