# OAuth System Migration Guide

This guide explains how to migrate from the old OAuth implementation to the new automated OAuth system.

## Overview

The new OAuth system provides automatic OAuth setup based on credential models. By simply defining a credential model with OAuth metadata, the system automatically:

1. Registers the OAuth client with authlib
2. Creates login and callback routes
3. Adds the service to the OAuth dashboard
4. Handles token storage and refresh

## Key Components

### 1. OAuthCredentialMixin

Base class for all OAuth credentials that provides:
- Standard OAuth fields: `oauth_refresh_token`, `oauth_access_token`, `oauth_token_expires_at`
- Automatic registration via metaclass (no decorator needed!)
- Base implementation of `from_oauth_callback()`

### 2. OAuthConfig

Configuration dataclass that defines OAuth provider settings.

### 3. Automatic Discovery

OAuth models are automatically discovered and registered when they inherit from `OAuthCredentialMixin` - no manual imports or decorators required!

## Migration Steps

### Step 1: Update Credential Models

Convert your existing OAuth credential models to use the new system:

```python
from standard_pipelines.api.oauth_system import OAuthCredentialMixin, OAuthConfig

class GoogleCredentials(OAuthCredentialMixin):
    """Credentials for Google API access."""
    __tablename__ = 'google_credential'
    
    # Add any provider-specific fields
    user_email: Mapped[str] = mapped_column(String(255))
    user_name: Mapped[Optional[str]] = mapped_column(String(255))
    
    @classmethod
    def get_oauth_config(cls) -> OAuthConfig:
        return OAuthConfig(
            name='google',
            display_name='Google',
            client_id_env='GOOGLE_CLIENT_ID',
            client_secret_env='GOOGLE_CLIENT_SECRET',
            # ... other config
        )
```

### Step 2: Remove Old OAuth Routes

Delete the manual OAuth routes from your API blueprints:
- Remove `/api/{provider}/oauth/login` routes
- Remove `/api/{provider}/oauth/authorize` routes

The new system creates these automatically.

### Step 3: Update Application Initialization

In your main application initialization:

```python
from standard_pipelines.api.oauth_init import init_oauth_system

def create_app():
    app = Flask(__name__)
    # ... other initialization
    
    # Initialize OAuth system
    init_oauth_system(app)
    
    return app
```

### Step 4: Update OAuth Dashboard

The OAuth dashboard now automatically discovers all registered OAuth services. The template has been updated to support the new `display_name` field.

### Step 5: Handle Database Migration

The new system adds standard OAuth fields to all OAuth credentials. You may need to create a database migration to:
1. Add new columns (`oauth_refresh_token`, `oauth_access_token`, `oauth_token_expires_at`)
2. Migrate data from old column names to new ones
3. Remove old OAuth-specific columns if desired

## Benefits of the New System

1. **Less Code Duplication**: OAuth routes are generated automatically
2. **Consistent Implementation**: All OAuth providers follow the same pattern
3. **Easy to Add New Providers**: Just create a model with `@oauth_credential`
4. **Automatic Dashboard Integration**: Services appear automatically in the OAuth dashboard
5. **Better Type Safety**: Using typed dataclasses for configuration

## Example: Adding a New OAuth Provider

To add a new OAuth provider (e.g., Slack), simply create a new model file:

```python
# standard_pipelines/api/slack/models.py
from standard_pipelines.api.oauth_system import OAuthCredentialMixin, OAuthConfig

class SlackCredentials(OAuthCredentialMixin):
    __tablename__ = 'slack_credential'
    
    team_id: Mapped[str] = mapped_column(String(255))
    team_name: Mapped[str] = mapped_column(String(255))
    
    @classmethod
    def get_oauth_config(cls) -> OAuthConfig:
        return OAuthConfig(
            name='slack',
            display_name='Slack',
            client_id_env='SLACK_CLIENT_ID',
            client_secret_env='SLACK_CLIENT_SECRET',
            authorize_url='https://slack.com/oauth/v2/authorize',
            access_token_url='https://slack.com/api/oauth.v2.access',
            api_base_url='https://slack.com/api/',
            scopes=['channels:read', 'chat:write'],
            icon_path='img/oauth/slack.svg',
            description='Connect to Slack for notifications'
        )
```

That's it! The provider will automatically be:
1. Discovered on app startup
2. Registered with the OAuth system
3. Available in the OAuth dashboard
4. Have working OAuth routes at `/api/oauth/slack/login` and `/api/oauth/slack/callback`

No manual registration, no imports, no decorators needed!

## Backward Compatibility

During migration, you can run both systems side-by-side:
1. Keep old routes active while testing new ones
2. The OAuth dashboard will show both old and new services
3. Gradually migrate each provider
4. Remove old code once migration is complete