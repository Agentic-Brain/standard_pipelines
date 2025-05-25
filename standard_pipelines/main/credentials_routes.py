"""
User-facing credentials management routes
"""
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from uuid import UUID
from typing import Dict, List, Any, Optional

from ..extensions import db
from ..data_flow.models import Client
from . import main

# Import all credential models
from ..auth.models import AnthropicCredentials
from ..api.openai.models import OpenAICredentials
from ..api.google.models import GoogleCredentials
from ..api.zoho.models import ZohoCredentials
from ..api.dialpad.models import DialpadCredentials
from ..api.sharpspring.models import SharpSpringCredentials
from ..api.fireflies.models import FirefliesCredentials
from ..api.hubspot.models import HubSpotCredentials

# Credential models registry
# TODO: Gonna wanna make this into a global registry of some sort to auto populate
# See dataflow registry meta for examples
# TODO: Fix icon drawing using credential logo type
CREDENTIAL_MODELS = {
    'anthropic': {
        'model': AnthropicCredentials,
        'name': 'Anthropic',
        'description': 'AI assistant API for advanced language processing',
        'icon': 'robot',
        'fields_info': {
            'anthropic_api_key': {'label': 'API Key', 'placeholder': 'sk-ant-...', 'help': 'Your Anthropic API key'}
        }
    },
    'openai': {
        'model': OpenAICredentials,
        'name': 'OpenAI',
        'description': 'GPT models for text generation and analysis',
        'icon': 'brain',
        'fields_info': {
            'openai_api_key': {'label': 'API Key', 'placeholder': 'sk-...', 'help': 'Your OpenAI API key'}
        }
    },
    'google': {
        'model': GoogleCredentials,
        'name': 'Google',
        'description': 'Google Workspace integration (Gmail, Drive, etc.)',
        'icon': 'google',
        'fields_info': {
            'refresh_token': {'label': 'Refresh Token', 'placeholder': 'Token', 'help': 'OAuth refresh token'},
            'scope': {'label': 'Scopes', 'placeholder': 'https://www.googleapis.com/auth/gmail.readonly', 'help': 'Space-separated API scopes'}
        }
    },
    'zoho': {
        'model': ZohoCredentials,
        'name': 'Zoho',
        'description': 'Zoho CRM and suite integration',
        'icon': 'building',
        'fields_info': {
            'account_url': {'label': 'Account URL', 'placeholder': 'https://accounts.zoho.com', 'help': 'Your Zoho account URL'},
            'refresh_token': {'label': 'Refresh Token', 'placeholder': 'Token', 'help': 'OAuth refresh token'}
        }
    },
    'dialpad': {
        'model': DialpadCredentials,
        'name': 'Dialpad',
        'description': 'Business phone and communication platform',
        'icon': 'phone',
        'fields_info': {
            'dialpad_api_key': {'label': 'API Key', 'placeholder': 'Your API key', 'help': 'Dialpad API key'},
            'jwt_secret': {'label': 'JWT Secret', 'placeholder': 'Secret', 'help': 'JWT secret for webhooks'}
        }
    },
    'sharpspring': {
        'model': SharpSpringCredentials,
        'name': 'SharpSpring',
        'description': 'Marketing automation and CRM platform',
        'icon': 'chart-line',
        'fields_info': {
            'account_id': {'label': 'Account ID', 'placeholder': 'Your account ID', 'help': 'SharpSpring account ID'},
            'secret_key': {'label': 'Secret Key', 'placeholder': 'Your secret key', 'help': 'SharpSpring secret key'}
        }
    },
    'fireflies': {
        'model': FirefliesCredentials,
        'name': 'Fireflies.ai',
        'description': 'AI meeting assistant and transcription',
        'icon': 'microphone',
        'fields_info': {
            'fireflies_api_key': {'label': 'API Key', 'placeholder': 'Your API key', 'help': 'Fireflies API key'}
        }
    },
    'hubspot': {
        'model': HubSpotCredentials,
        'name': 'HubSpot',
        'description': 'Marketing, sales, and service platform',
        'icon': 'hubspot',
        'fields_info': {
            'access_token': {'label': 'Access Token', 'placeholder': 'Token', 'help': 'HubSpot access token'},
            'refresh_token': {'label': 'Refresh Token', 'placeholder': 'Token', 'help': 'HubSpot refresh token'}
        }
    }
}
# LOG: Add error loggin to this entire section
# Fields to exclude from display (encrypted fields)
# TODO: This sucks, gonna want to change it as well
# TODO: Possible defaults plus override on a per model basis? Look into working with the actual DB model
# Hiding all by default and only revealing what is requested is probably a better idea
ENCRYPTED_FIELDS = {
    'api_key', 'secret', 'password', 'token', 'refresh_token',
    'client_secret', 'private_key', 'jwt_secret', 'anthropic_api_key',
    'openai_api_key', 'dialpad_api_key', 'fireflies_api_key', 'access_token',
    'secret_key'
}


def get_user_client() -> Optional[Client]:
    """Get the client associated with the current user"""
    if not current_user.is_authenticated:
        return None
    return current_user.client

# TODO: Set credentials as "enabled" for certain clients so they can only see what is relevant
# TODO: Don't display oauth credentials here
@main.route('/credentials')
@login_required
def credentials():
    """User credentials management page"""
    client = get_user_client()
    if not client:
        flash('No client associated with your account', 'error')
        # This should not be possible, user should always have associated client
        current_app.logger.error(f'User {current_user} tried to access credentials without associated client')
        return redirect(url_for('main.index'))
    
    # Get all credentials for this client
    user_credentials = {}
    # TODO: Change this to registry model as mentioned above
    for key, info in CREDENTIAL_MODELS.items():
        model = info['model']
        creds = db.session.query(model).filter_by(client_id=client.id).all()
        user_credentials[key] = {
            'info': info,
            'credentials': creds,
            'count': len(creds)
        }
    
    return render_template('credentials.html',
                         client=client,
                         credential_types=user_credentials)


@main.route('/credentials/add/<credential_type>', methods=['GET', 'POST'])
@login_required
def add_credential(credential_type: str):
    """Add a new credential"""
    if credential_type not in CREDENTIAL_MODELS:
        flash('Invalid credential type', 'error')
        return redirect(url_for('main.credentials'))
    
    client = get_user_client()
    if not client:
        flash('No client associated with your account', 'error')
        return redirect(url_for('main.index'))
    
    cred_info = CREDENTIAL_MODELS[credential_type]
    model = cred_info['model']
    
    if request.method == 'POST':
        try:
            # Collect all form data including client_id
            kwargs = {'client_id': client.id}
            for field in request.form:
                if field != 'client_id':
                    kwargs[field] = request.form[field]
            
            # Create new credential instance with all data
            credential = model(**kwargs)
            credential.client_id = client.id
            
            db.session.add(credential)
            db.session.commit()
            
            flash(f'{cred_info["name"]} credential added successfully', 'success')
            return redirect(url_for('main.credentials'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding credential: {str(e)}', 'error')
    
    # Get model fields for form
    fields = []
    for column in model.__table__.columns:
        # TODO: Find a way to define this as "non-viewable" in the base credentials model
        if column.name not in ['id', 'client_id', 'created_at', 'updated_at', 'modified_at']:
            field_info = {
                'name': column.name,
                'type': str(column.type),
                'required': not column.nullable,
                'is_encrypted': column.name in ENCRYPTED_FIELDS
            }
            # Add field-specific info if available
            if column.name in cred_info.get('fields_info', {}):
                field_info.update(cred_info['fields_info'][column.name])
            fields.append(field_info)
    
    return render_template('add_credential.html',
                         client=client,
                         credential_type=credential_type,
                         credential_info=cred_info,
                         fields=fields)


@main.route('/credentials/delete/<credential_type>/<uuid:credential_id>', methods=['POST'])
@login_required
def delete_credential(credential_type: str, credential_id: UUID):
    """Delete a credential"""
    if credential_type not in CREDENTIAL_MODELS:
        return jsonify({'error': 'Invalid credential type'}), 400
    
    client = get_user_client()
    if not client:
        return jsonify({'error': 'No client associated with your account'}), 403
    
    model = CREDENTIAL_MODELS[credential_type]['model']
    credential = db.session.get(model, credential_id)
    
    if not credential or credential.client_id != client.id:
        return jsonify({'error': 'Credential not found'}), 404
    
    try:
        db.session.delete(credential)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500