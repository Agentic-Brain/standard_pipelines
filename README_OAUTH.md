# Standard Pipelines - OAuth Integration System

## Table of Contents
- [Overview](#overview)
- [How It Works](#how-it-works)
- [Adding a New OAuth Provider](#adding-a-new-oauth-provider)
- [OAuth System Architecture](#oauth-system-architecture)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

## Overview

Standard Pipelines features an automated OAuth integration system that makes adding new OAuth providers as simple as defining a credential model. The system automatically handles:

- OAuth client registration with authlib
- Route generation for login and callback endpoints
- Token storage and management
- Encryption of sensitive credentials
- Integration with the OAuth dashboard
- Backward compatibility with legacy implementations

## How It Works

### Automatic Discovery and Registration

When the application starts, the OAuth system automatically:

1. **Discovers OAuth Models**: Scans the `api` directory for any models that inherit from `OAuthCredentialMixin`
2. **Registers OAuth Clients**: For each discovered model, registers an OAuth client with authlib using the configuration from `get_oauth_config()`
3. **Creates Routes**: Generates standardized OAuth routes for each provider
4. **Updates Dashboard**: Makes the provider available in the OAuth dashboard at `/auth/oauth`

### OAuth Flow

The standard OAuth flow works as follows:

1. User visits `/auth/oauth` and clicks "Connect" for a provider
2. User is redirected to `/api/oauth/{provider}/login`
3. System redirects to the provider's authorization page
4. Provider redirects back to `/api/oauth/{provider}/callback`
5. System exchanges the authorization code for tokens
6. Tokens are encrypted and stored in the database
7. User sees a success page

### Security

All OAuth credentials are encrypted using:
- Bitwarden for key management
- Fernet encryption for token storage
- Client-specific encryption keys
- Secure token refresh handling

## Adding a New OAuth Provider

Adding a new OAuth provider requires just one file - a model definition. Here's a step-by-step guide:

### Step 1: Create the Model File

Create a new file at `standard_pipelines/api/{provider}/models.py`:

```python
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Dict, Any

from standard_pipelines.api.oauth_system import OAuthCredentialMixin, OAuthConfig


class YourProviderCredentials(OAuthCredentialMixin):
    """Credentials for YourProvider API access."""
    __tablename__ = 'yourprovider_credential'
    __abstract__ = False  # Important: Mark as concrete implementation
    
    # Add any provider-specific fields
    user_id: Mapped[str] = mapped_column(String(255))
    workspace_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    def __init__(self, client_id: UUID, **kwargs):
        self.client_id = client_id
        super().__init__(**kwargs)
    
    @classmethod
    def get_oauth_config(cls) -> OAuthConfig:
        return OAuthConfig(
            # Basic configuration
            name='yourprovider',  # URL-safe name for routes
            display_name='YourProvider',  # Display name for UI
            
            # Environment variables for OAuth app credentials
            client_id_env='YOURPROVIDER_CLIENT_ID',
            client_secret_env='YOURPROVIDER_CLIENT_SECRET',
            
            # OAuth endpoints
            authorize_url='https://yourprovider.com/oauth/authorize',
            access_token_url='https://yourprovider.com/oauth/token',
            api_base_url='https://api.yourprovider.com/',
            
            # OAuth scopes required
            scopes=['read', 'write'],
            
            # UI configuration
            icon_path='img/oauth/yourprovider.svg',
            description='Connect to YourProvider for data sync',
            
            # Optional: User info endpoint for fetching profile data
            user_info_endpoint='https://api.yourprovider.com/user',
            user_info_fields={
                'user_id': 'id',  # Map model field to API response field
                'workspace_name': 'workspace.name'
            },
            
            # Optional: Extra parameters for authorization
            extra_authorize_params={
                'response_type': 'code',
                'prompt': 'consent'
            },
            
            # Optional: Token endpoint authentication method
            token_endpoint_auth_method='client_secret_post'  # or 'client_secret_basic'
        )
    
    @classmethod
    def from_oauth_callback(cls, client_id, token: Dict[str, Any], user_info: Dict[str, Any] = None):
        """
        Optional: Override to handle custom token response data.
        Called after successful OAuth callback.
        """
        instance = super().from_oauth_callback(client_id, token, user_info)
        
        # Handle any custom fields from the token response
        if 'workspace' in token:
            instance.workspace_name = token['workspace']['name']
        
        return instance
```

### Step 2: Add Provider Icon

Add an SVG icon for your provider at `standard_pipelines/static/img/oauth/yourprovider.svg`.

### Step 3: Create Database Migration

```bash
uv run flask db migrate -m "Add YourProvider OAuth credentials"
uv run flask db upgrade
```

### Step 4: Set Environment Variables

Add to your `.env` file:
```
YOURPROVIDER_CLIENT_ID=your_oauth_app_client_id
YOURPROVIDER_CLIENT_SECRET=your_oauth_app_client_secret
```

### Step 5: Create API Routes (Optional)

If you need additional API endpoints beyond OAuth, create `standard_pipelines/api/{provider}/routes.py`:

```python
from flask import jsonify
from flask_login import login_required, current_user
from standard_pipelines.api import api
from standard_pipelines.api.yourprovider.models import YourProviderCredentials


@api.route('/yourprovider/test')
@login_required
def test_yourprovider_connection():
    """Test the YourProvider connection."""
    credentials = YourProviderCredentials.query.filter_by(
        client_id=current_user.client_id
    ).first()
    
    if not credentials:
        return jsonify({'error': 'Not connected to YourProvider'}), 404
    
    return jsonify({
        'connected': True,
        'user_id': credentials.user_id
    })
```

### That's It!

Your provider will now:
- ✅ Appear in the OAuth dashboard at `/auth/oauth`
- ✅ Have working OAuth routes at:
  - `/api/oauth/yourprovider/login` - Initiates OAuth flow
  - `/api/oauth/yourprovider/callback` - Handles OAuth callback
- ✅ Store encrypted credentials in the database
- ✅ Be available for use in your application

## OAuth System Architecture

### Core Components

#### 1. OAuthCredentialMixin

Base class that all OAuth credential models inherit from. Provides:
- Standard OAuth fields: `oauth_refresh_token`, `oauth_access_token`, `oauth_token_expires_at`
- Automatic registration via `__init_subclass__`
- Encryption through `SecureMixin` inheritance
- Default `from_oauth_callback()` implementation

#### 2. OAuthConfig Dataclass

Configuration container with the following fields:
- `name`: URL-safe identifier for the provider
- `display_name`: Human-readable name
- `client_id_env`, `client_secret_env`: Environment variable names
- `authorize_url`, `access_token_url`: OAuth endpoints
- `api_base_url`: Base URL for API calls
- `scopes`: List of OAuth scopes
- `icon_path`: Path to provider icon
- `description`: Provider description for UI
- `user_info_endpoint`: (Optional) Endpoint to fetch user profile
- `user_info_fields`: (Optional) Mapping of model fields to API response
- `extra_authorize_params`: (Optional) Additional authorization parameters
- `token_endpoint_auth_method`: (Optional) Authentication method

#### 3. OAuth Discovery System

- `oauth_discovery.py`: Automatically finds and imports OAuth models
- `oauth_init.py`: Initializes the OAuth system during app startup
- Uses Python's `__init_subclass__` for automatic registration

#### 4. Route Generation

The system automatically creates two routes per provider:
- Login route: Initiates OAuth flow with proper redirect URI
- Callback route: Handles provider callback, exchanges code for tokens

### File Structure

```
standard_pipelines/
├── api/
│   ├── oauth_system.py      # Core OAuth system
│   ├── oauth_discovery.py   # Model discovery logic
│   ├── oauth_init.py        # System initialization
│   └── {provider}/
│       ├── __init__.py
│       ├── models.py        # OAuth credential model
│       ├── routes.py        # (Optional) API routes
│       └── services.py      # (Optional) API manager
├── static/img/oauth/        # Provider icons
└── templates/
    ├── oauth.html           # OAuth dashboard
    └── auth/
        └── oauth_success.html  # Success page
```

## API Reference

### OAuthCredentialMixin Methods

#### get_oauth_config() -> OAuthConfig
**Required**. Returns the OAuth configuration for the provider.

#### from_oauth_callback(client_id, token, user_info) -> Self
**Optional**. Creates a credential instance from OAuth callback data.

### Backward Compatibility

For migrated models, backward compatibility can be maintained using SQLAlchemy's `@hybrid_property`:

```python
from sqlalchemy.ext.hybrid import hybrid_property

class GoogleCredentials(OAuthCredentialMixin):
    # ... other fields ...
    
    @hybrid_property
    def refresh_token(self):
        """Backward compatibility for old field name."""
        return self.oauth_refresh_token
    
    @refresh_token.setter
    def refresh_token(self, value):
        """Backward compatibility for old field name."""
        self.oauth_refresh_token = value
```

### Token Refresh

Token refresh is handled automatically by API managers. Example:

```python
class YourProviderAPIManager(BaseAPIManager):
    def __init__(self, credentials: YourProviderCredentials):
        self.credentials = credentials
        
    def _refresh_token_if_needed(self):
        """Refresh the access token if it has expired."""
        if self._is_token_expired():
            # Implement token refresh logic
            pass
```

## Troubleshooting

### Provider Not Appearing in Dashboard

1. Ensure the model has `__abstract__ = False`
2. Check that the model inherits from `OAuthCredentialMixin`
3. Verify `get_oauth_config()` returns a valid `OAuthConfig`
4. Check logs for import errors during discovery

### OAuth Flow Failing

1. Verify environment variables are set correctly
2. Check that OAuth URLs are correct in `get_oauth_config()`
3. Ensure redirect URI matches provider configuration
4. Check logs for specific error messages

### Credentials Not Storing

1. Ensure database migration has been run
2. Check that Bitwarden encryption is configured
3. Verify the client has an encryption key set
4. Check for unique constraint violations

### Common Issues

**Issue**: "Missing OAuth credentials" warning in logs
**Solution**: Set the required environment variables for the provider

**Issue**: Routes not created for new provider
**Solution**: Restart the application to trigger discovery

**Issue**: Icon not showing in dashboard
**Solution**: Add SVG icon at the path specified in `icon_path`

---

For more information or to report issues, please refer to the main project documentation.