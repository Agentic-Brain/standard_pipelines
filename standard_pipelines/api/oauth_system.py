"""
OAuth System - Automatic OAuth setup based on credential models.

This module provides a decorator-based system for automatically configuring OAuth
for any API by simply defining a credential model with OAuth metadata.
"""

from typing import Type, Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from flask import Blueprint, current_app, url_for, jsonify, render_template
from flask_login import login_required, current_user
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.exc import SQLAlchemyError
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
    oauth_refresh_token: Mapped[str] = mapped_column(String(512))
    oauth_access_token: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    oauth_token_expires_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
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
    def from_oauth_callback(cls, client_id, token: Dict[str, Any], user_info: Dict[str, Any] = None) -> 'OAuthCredentialMixin':
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
            else:
                # Create new credentials
                new_creds = credential_cls.from_oauth_callback(client.id, token, user_info)
                db.session.add(new_creds)
                db.session.commit()
                current_app.logger.info(f"Created new {provider} credentials for client: {client.name}")
            
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