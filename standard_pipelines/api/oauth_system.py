"""
OAuth System - Automatic OAuth setup based on credential models.

This module provides a decorator-based system for automatically configuring OAuth
for any API by simply defining a credential model with OAuth metadata.
"""

from typing import Type, Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from flask import Blueprint, current_app, url_for, jsonify, render_template
from flask_login import login_required, current_user
from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.exc import SQLAlchemyError
from standard_pipelines.database.models import unencrypted_mapped_column
from authlib.integrations.base_client.errors import OAuthError
import requests
from functools import wraps
import inspect

from standard_pipelines.extensions import db, oauth
from standard_pipelines.auth.models import BaseCredentials
from standard_pipelines.data_flow.models import Client


@dataclass
class OAuthConfig:
    """Configuration for an OAuth provider."""
    name: str
    display_name: str
    client_id_env: str
    client_secret_env: str
    authorize_url: str
    access_token_url: str
    api_base_url: str
    scopes: List[str]
    icon_path: str
    description: str
    user_info_endpoint: Optional[str] = None
    user_info_fields: Dict[str, str] = field(default_factory=dict)
    extra_authorize_params: Dict[str, Any] = field(default_factory=dict)
    token_endpoint_auth_method: str = 'client_secret_post'


# Global registry of OAuth-enabled credential models
_oauth_registry: Dict[str, Type['OAuthCredentialMixin']] = {}


class OAuthCredentialMixin(BaseCredentials):
    """
    Base mixin for OAuth credentials.
    All OAuth credential models should inherit from this.
    """
    __abstract__ = True
    
    # OAuth tokens - these are standard across all OAuth providers
    oauth_refresh_token: Mapped[str] = mapped_column(Text)
    oauth_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    oauth_token_expires_at: Mapped[Optional[int]] = unencrypted_mapped_column(Integer, nullable=True)
    
    def __init_subclass__(cls, **kwargs):
        """Automatically register OAuth credential models."""
        super().__init_subclass__(**kwargs)
        
        # Skip abstract classes
        if not getattr(cls, '__abstract__', False):
            # Check if this class has get_oauth_config method
            if hasattr(cls, 'get_oauth_config') and callable(getattr(cls, 'get_oauth_config')):
                try:
                    config = cls.get_oauth_config()
                    if config:
                        _oauth_registry[config.name] = cls
                        if current_app:
                            current_app.logger.debug(f"Registered OAuth model {cls.__name__} as {config.name}")
                except Exception as e:
                    # Log errors during class creation if possible
                    if current_app:
                        current_app.logger.warning(f"Error registering {cls.__name__}: {e}")
    
    @classmethod
    def get_oauth_config(cls) -> Optional[OAuthConfig]:
        """Get OAuth configuration. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement get_oauth_config()")
    
    @classmethod
    def get_n8n_credential_types(cls) -> List[str]:
        """
        Get list of N8N credential types this OAuth credential should create.
        Return empty list if no N8N integration needed.
        
        Examples:
        - Google: ['gmailOAuth2Api', 'googleCalendarOAuth2Api'] 
        - Office365: ['microsoftOutlookOAuth2Api']
        - HubSpot: ['hubspotOAuth2Api']
        """
        return []
    
    def sync_to_n8n(self, user_email: str) -> bool:
        """
        Sync this credential to N8N.
        
        Args:
            user_email: Email of the user who completed the OAuth flow
            
        Returns:
            True if successful, False otherwise.
        """
        from standard_pipelines.data_flow.models import Client
        
        n8n_types = self.get_n8n_credential_types()
        if not n8n_types:
            return True  # No N8N sync needed
        
        try:
            # Get client info for naming
            client = Client.query.get(self.client_id)
            if not client:
                current_app.logger.error(f"Client {self.client_id} not found for N8N sync")
                return False
            
            service_name = self.get_oauth_config().display_name if self.get_oauth_config() else self.__class__.__name__
            
            success = True
            for n8n_type in n8n_types:
                credential_name = f"{client.name} - {user_email} - {service_name}"
                if not _sync_credential_to_n8n(self, n8n_type, credential_name):
                    success = False
            
            return success
            
        except Exception as e:
            current_app.logger.error(f"Error syncing {self.__class__.__name__} to N8N: {e}")
            return False
    
    @classmethod
    def from_oauth_callback(cls, client_id, token: Dict[str, Any], user_info: Optional[Dict[str, Any]] = None) -> 'OAuthCredentialMixin':
        """
        Create credential instance from OAuth callback data.
        Can be overridden by subclasses for custom behavior.
        """
        instance = cls(client_id=client_id)
        instance.oauth_refresh_token = token.get('refresh_token', '')
        instance.oauth_access_token = token.get('access_token', '')
        instance.oauth_token_expires_at = token.get('expires_at')
        
        # Map user info fields if configured
        if user_info and hasattr(cls, 'get_oauth_config'):
            config = cls.get_oauth_config()
            if config and config.user_info_fields:
                for attr_name, info_key in config.user_info_fields.items():
                    if hasattr(instance, attr_name) and info_key in user_info:
                        setattr(instance, attr_name, user_info[info_key])
        
        return instance


def oauth_credential(cls: Type[OAuthCredentialMixin]) -> Type[OAuthCredentialMixin]:
    """
    Decorator to register an OAuth credential model.
    This automatically sets up OAuth client registration and routes.
    
    Note: This decorator is now optional if the class uses OAuthCredentialMixin
    with its metaclass. It's kept for backward compatibility and explicit registration.
    """
    if not issubclass(cls, OAuthCredentialMixin):
        raise ValueError(f"{cls.__name__} must inherit from OAuthCredentialMixin")
    
    # Get OAuth config
    config = cls.get_oauth_config()
    if not config:
        raise ValueError(f"{cls.__name__} must implement get_oauth_config()")
    
    # Register in global registry
    _oauth_registry[config.name] = cls
    
    return cls


def register_oauth_clients(app):
    """Register all OAuth clients from the registry."""
    app.logger.info(f"Registering {len(_oauth_registry)} OAuth clients from registry")
    
    for name, credential_cls in _oauth_registry.items():
        config = credential_cls.get_oauth_config()
        if not config:
            continue
            
        # Get client credentials from environment
        client_id = app.config.get(config.client_id_env)
        client_secret = app.config.get(config.client_secret_env)
        
        if not client_id or not client_secret:
            app.logger.warning(f"Missing OAuth credentials for {config.display_name} (env: {config.client_id_env}, {config.client_secret_env})")
            continue
        
        app.logger.info(f"Registering OAuth client for {config.display_name}")
        
        # Register with authlib
        oauth.register(
            name=config.name,
            client_id=client_id,
            client_secret=client_secret,
            access_token_url=config.access_token_url,
            authorize_url=config.authorize_url,
            api_base_url=config.api_base_url,
            client_kwargs={
                'scope': ' '.join(config.scopes),
                'token_endpoint_auth_method': config.token_endpoint_auth_method
            }
        )


def create_oauth_routes() -> Blueprint:
    """Create OAuth routes for all registered providers."""
    oauth_bp = Blueprint('oauth_system', __name__, url_prefix='/api/oauth')
    
    # Create routes for each registered OAuth provider
    for name, credential_cls in _oauth_registry.items():
        config = credential_cls.get_oauth_config()
        if not config:
            continue
        
        # Create login route
        @oauth_bp.route(f'/{name}/login')
        @login_required
        def oauth_login(provider_name=name):
            """Initiate OAuth flow."""
            try:
                oauth_client = getattr(oauth, provider_name)
                if oauth_client is None:
                    return jsonify({'error': f'{provider_name} OAuth client not initialized'}), 500
                
                redirect_uri = url_for(
                    'oauth_system.oauth_callback',
                    provider=provider_name,
                    _external=True,
                    _scheme=current_app.config.get('PREFERRED_URL_SCHEME', 'https')
                )
                
                # Get extra params from config
                provider_config = _oauth_registry[provider_name].get_oauth_config()
                extra_params = provider_config.extra_authorize_params if provider_config else {}
                
                return oauth_client.authorize_redirect(redirect_uri, **extra_params)
                
            except Exception as e:
                current_app.logger.error(f"Error in OAuth login for {provider_name}: {e}")
                return jsonify({'error': 'Failed to initiate OAuth flow'}), 500
        
        # Register the route with a unique endpoint name
        oauth_login.__name__ = f'login_{name}'
    
    # Single callback route that handles all providers
    @oauth_bp.route('/<provider>/callback')
    @login_required
    def oauth_callback(provider):
        """Handle OAuth callback for any provider."""
        if provider not in _oauth_registry:
            return jsonify({'error': 'Invalid provider'}), 404
        
        try:
            oauth_client = getattr(oauth, provider)
            if oauth_client is None:
                return jsonify({'error': f'{provider} OAuth client not initialized'}), 500
            
            # Exchange code for token
            token = oauth_client.authorize_access_token()
            if not token:
                return jsonify({'error': 'Failed to retrieve access token'}), 400
            
            current_app.logger.info(f"Successfully obtained {provider} access token")
            
            # Get credential class and config
            credential_cls = _oauth_registry[provider]
            config = credential_cls.get_oauth_config()
            
            # Fetch user info if endpoint is configured
            user_info = {}
            if config and config.user_info_endpoint and token.get('access_token'):
                try:
                    headers = {"Authorization": f"Bearer {token['access_token']}"}
                    response = requests.get(config.user_info_endpoint, headers=headers)
                    response.raise_for_status()
                    user_info = response.json()
                except Exception as e:
                    current_app.logger.error(f"Error fetching user info: {e}")
            
            # Get client
            client = Client.query.get_or_404(current_user.client_id)
            
            # Create or update credentials
            existing = credential_cls.query.filter_by(client_id=client.id).first()
            
            if existing:
                # Update existing credentials
                existing.oauth_refresh_token = token.get('refresh_token', existing.oauth_refresh_token)
                existing.oauth_access_token = token.get('access_token')
                existing.oauth_token_expires_at = token.get('expires_at')
                
                # Update user info fields if configured
                if user_info and config and config.user_info_fields:
                    for attr_name, info_key in config.user_info_fields.items():
                        if hasattr(existing, attr_name) and info_key in user_info:
                            setattr(existing, attr_name, user_info[info_key])
                
                db.session.commit()
                current_app.logger.info(f"Updated {provider} credentials for client: {client.name}")
                
                # Sync updated credentials to N8N
                existing.sync_to_n8n(current_user.email)
                
            else:
                # Create new credentials
                new_creds = credential_cls.from_oauth_callback(client.id, token, user_info)
                db.session.add(new_creds)
                db.session.commit()
                current_app.logger.info(f"Created new {provider} credentials for client: {client.name}")
                
                # Sync new credentials to N8N
                new_creds.sync_to_n8n(current_user.email)
            
            # Render success page
            return render_template('auth/oauth_success.html', service=config.display_name if config else provider)
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in OAuth callback: {e}")
            return jsonify({'error': 'Failed to save credentials'}), 500
        except Exception as e:
            current_app.logger.error(f"Error in OAuth callback for {provider}: {e}")
            return jsonify({'error': 'Authorization failed'}), 500
    
    return oauth_bp


def _sync_credential_to_n8n(credential: OAuthCredentialMixin, n8n_type: str, credential_name: str) -> bool:
    """
    Sync a single credential to N8N.
    
    Args:
        credential: The OAuth credential instance
        n8n_type: The N8N credential type (e.g., 'gmailOAuth2Api')
        credential_name: The name to use in N8N
        
    Returns:
        True if successful, False otherwise
    """
    try:
        n8n_endpoint = current_app.config.get('N8N_ENDPOINT')
        n8n_api_key = current_app.config.get('N8N_API_KEY')
        
        if not n8n_api_key or not n8n_endpoint:
            current_app.logger.warning("N8N_API_KEY not configured, skipping N8N sync")
            return False
        
        # Get OAuth config
        oauth_config = credential.get_oauth_config()
        if not oauth_config:
            current_app.logger.error(f"No OAuth config found for {credential.__class__.__name__}")
            return False
        
        # Prepare credential data for N8N based on credential type
        if n8n_type == 'microsoftOutlookOAuth2Api':
            # Microsoft Outlook OAuth2 API expects specific format
            credential_data = {
                'name': credential_name,
                'type': n8n_type,
                'data': {
                    'clientId': current_app.config.get(oauth_config.client_id_env),
                    'clientSecret': current_app.config.get(oauth_config.client_secret_env),
                    'userPrincipalName': getattr(credential, 'user_principal_name', ''),
                }
            }
        else:
            # Generic OAuth2 format for other services
            credential_data = {
                'name': credential_name,
                'type': n8n_type,
                'data': {
                    'clientId': current_app.config.get(oauth_config.client_id_env),
                    'clientSecret': current_app.config.get(oauth_config.client_secret_env),
                    'accessToken': credential.oauth_access_token,
                    'refreshToken': credential.oauth_refresh_token,
                }
            }
            
            # Add expires information if available
            if credential.oauth_token_expires_at:
                credential_data['data']['expiresAt'] = credential.oauth_token_expires_at
        
        headers = {
            'Content-Type': 'application/json',
            'X-N8N-API-KEY': n8n_api_key
        }
        
        response = requests.post(n8n_endpoint, json=credential_data, headers=headers)
        
        if response.status_code in [200, 201]:
            current_app.logger.info(f"Successfully synced {credential_name} to N8N as {n8n_type}")
            return True
        else:
            current_app.logger.error(f"Failed to sync to N8N: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error syncing credential to N8N: {e}")
        return False


def get_oauth_services_status(client_id) -> Dict[str, Dict[str, Any]]:
    """Get the status of all OAuth services for a client."""
    services = {}
    
    for name, credential_cls in _oauth_registry.items():
        config = credential_cls.get_oauth_config()
        if not config:
            continue
        
        # Check if service is enabled (credentials are in config)
        client_id_env = config.client_id_env
        client_secret_env = config.client_secret_env
        enabled = bool(
            current_app.config.get(client_id_env) and 
            current_app.config.get(client_secret_env)
        )
        
        # Check if connected
        connected = credential_cls.query.filter_by(client_id=client_id).first() is not None
        
        services[name] = {
            'enabled': enabled,
            'connected': connected,
            'icon': url_for('static', filename=config.icon_path),
            'description': config.description,
            'display_name': config.display_name
        }
    
    return services