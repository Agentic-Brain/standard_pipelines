"""
Notion OAuth credentials using the new OAuth system.
"""
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Dict, Any

from standard_pipelines.api.oauth_system import OAuthCredentialMixin, OAuthConfig


class NotionCredentials(OAuthCredentialMixin):
    """Credentials for Notion API access."""
    __tablename__ = 'notion_credential'
    __abstract__ = False  # This is a concrete implementation
    
    # Override table args to remove unique constraint on client_id
    __table_args__ = ()
    
    # Notion-specific fields
    bot_id: Mapped[str] = mapped_column(String(255))
    workspace_id: Mapped[str] = mapped_column(String(255))
    workspace_name: Mapped[str] = mapped_column(String(255))
    workspace_icon: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # Owner information (can be user or workspace)
    owner_type: Mapped[str] = mapped_column(String(50))  # 'user' or 'workspace'
    owner_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_user_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    def __init__(self, client_id: UUID, **kwargs):
        self.client_id = client_id
        super().__init__(**kwargs)
    
    @classmethod
    def get_oauth_config(cls) -> OAuthConfig:
        return OAuthConfig(
            name='notion',
            display_name='Notion',
            client_id_env='NOTION_CLIENT_ID',
            client_secret_env='NOTION_CLIENT_SECRET',
            authorize_url='https://api.notion.com/v1/oauth/authorize',
            access_token_url='https://api.notion.com/v1/oauth/token',
            api_base_url='https://api.notion.com/v1/',
            scopes=[],  # Notion doesn't use scopes in the traditional OAuth sense
            icon_path='img/oauth/notion.svg',
            description='Connect to Notion for workspace integration',
            extra_authorize_params={
                'response_type': 'code',
                'owner': 'user'  # Always request user authorization
            },
            token_endpoint_auth_method='client_secret_basic'  # Use HTTP Basic Auth
        )
    
    @classmethod
    def from_oauth_callback(cls, client_id, token: Dict[str, Any], user_info: Dict[str, Any] = None) -> 'NotionCredentials':
        """
        Create credential instance from OAuth callback data.
        Notion returns additional data in the token response.
        """
        instance = super().from_oauth_callback(client_id, token, user_info)
        
        # Notion returns extra data in the token response itself
        instance.bot_id = token.get('bot_id', '')
        instance.workspace_id = token.get('workspace_id', '')
        instance.workspace_name = token.get('workspace_name', '')
        instance.workspace_icon = token.get('workspace_icon')
        
        # Handle owner information
        owner = token.get('owner', {})
        owner_type = owner.get('type', 'user')
        instance.owner_type = owner_type
        
        if owner_type == 'user':
            user_obj = owner.get('user', {})
            instance.owner_user_id = user_obj.get('id')
            instance.owner_user_name = user_obj.get('name')
            instance.owner_user_email = user_obj.get('person', {}).get('email')
        elif owner_type == 'workspace':
            # Workspace owner doesn't have user details
            instance.owner_user_id = None
            instance.owner_user_name = None
            instance.owner_user_email = None
        
        return instance