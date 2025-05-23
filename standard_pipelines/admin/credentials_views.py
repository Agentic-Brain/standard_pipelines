"""
Client credentials management views
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from uuid import UUID
from typing import Dict, List, Any

from ..extensions import db
from .routes import admin_required
from standard_pipelines.data_flow.models import Client
from . import admin

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
CREDENTIAL_MODELS = {
    'anthropic': AnthropicCredentials,
    'openai': OpenAICredentials,
    'google': GoogleCredentials,
    'zoho': ZohoCredentials,
    'dialpad': DialpadCredentials,
    'sharpspring': SharpSpringCredentials,
    'fireflies': FirefliesCredentials,
    'hubspot': HubSpotCredentials
}

# Fields to exclude from display (encrypted fields)
ENCRYPTED_FIELDS = {
    'api_key', 'secret', 'password', 'token', 'refresh_token',
    'client_secret', 'private_key', 'jwt_secret', 'anthropic_api_key',
    'openai_api_key', 'dialpad_api_key', 'fireflies_api_key'
}


@admin.route('/credentials')
@admin_required
def credentials_overview():
    """Show overview of all credential types and allow management"""
    # Get count of each credential type across all clients
    credential_counts = {}
    total_credentials = 0
    
    for name, model in CREDENTIAL_MODELS.items():
        count = db.session.query(model).count()
        credential_counts[name] = {
            'count': count,
            'model': model,
            'display_name': name.replace('_', ' ').title()
        }
        total_credentials += count
    
    # Get all clients for the dropdown
    clients = db.session.query(Client).filter_by(is_active=True).order_by(Client.name).all()
    
    return render_template('admin/credentials/overview.html',
                         credential_types=credential_counts,
                         total_credentials=total_credentials,
                         clients=clients)


@admin.route('/credentials/list/<credential_type>')
@admin_required
def list_credentials_by_type(credential_type: str):
    """List all credentials of a specific type"""
    if credential_type not in CREDENTIAL_MODELS:
        flash('Invalid credential type', 'error')
        return redirect(url_for('admin.credentials_overview'))
    
    model = CREDENTIAL_MODELS[credential_type]
    
    # Get all credentials of this type with their associated clients
    credentials = db.session.query(model).join(Client).order_by(Client.name).all()
    
    # Get viewable fields for this credential type
    viewable_fields = []
    for column in model.__table__.columns:
        if column.name not in ENCRYPTED_FIELDS and column.name not in ['id', 'client_id']:
            viewable_fields.append(column.name)
    
    # Get all clients for the dropdown
    clients = db.session.query(Client).filter_by(is_active=True).order_by(Client.name).all()
    
    return render_template('admin/credentials/list_by_type.html',
                         credential_type=credential_type,
                         credentials=credentials,
                         viewable_fields=viewable_fields,
                         clients=clients)


@admin.route('/client/<uuid:client_id>/credentials')
@admin_required
def client_credentials(client_id: UUID):
    """List all credentials for a specific client"""
    client = db.session.get(Client, client_id)
    if not client:
        flash('Client not found', 'error')
        return redirect(url_for('admin.index'))
    
    # Get all credentials for this client
    credentials = {}
    for name, model in CREDENTIAL_MODELS.items():
        creds = db.session.query(model).filter_by(client_id=client_id).all()
        if creds:
            credentials[name] = creds
    
    return render_template('admin/credentials/list.html',
                         client=client,
                         credentials=credentials,
                         credential_types=list(CREDENTIAL_MODELS.keys()))


@admin.route('/client/<uuid:client_id>/credentials/add/<credential_type>', methods=['GET', 'POST'])
@admin_required
def add_credential(client_id: UUID, credential_type: str):
    """Add a new credential for a client"""
    if credential_type not in CREDENTIAL_MODELS:
        flash('Invalid credential type', 'error')
        return redirect(url_for('admin.client_credentials', client_id=client_id))
    
    client = db.session.get(Client, client_id)
    if not client:
        flash('Client not found', 'error')
        return redirect(url_for('admin.index'))
    
    model = CREDENTIAL_MODELS[credential_type]
    
    if request.method == 'POST':
        try:
            # Create new credential instance
            credential = model()
            credential.client_id = client_id
            
            # Set fields from form
            for field in request.form:
                if hasattr(credential, field) and field != 'client_id':
                    setattr(credential, field, request.form[field])
            
            db.session.add(credential)
            db.session.commit()
            
            flash(f'{credential_type.title()} credential added successfully', 'success')
            return redirect(url_for('admin.client_credentials', client_id=client_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding credential: {str(e)}', 'error')
    
    # Get model fields for form
    fields = []
    for column in model.__table__.columns:
        if column.name not in ['id', 'client_id', 'created_at', 'updated_at']:
            field_info = {
                'name': column.name,
                'type': str(column.type),
                'required': not column.nullable,
                'is_encrypted': column.name in ENCRYPTED_FIELDS
            }
            fields.append(field_info)
    
    return render_template('admin/credentials/add.html',
                         client=client,
                         credential_type=credential_type,
                         fields=fields)


@admin.route('/client/<uuid:client_id>/credentials/delete/<credential_type>/<uuid:credential_id>', methods=['POST'])
@admin_required
def delete_credential(client_id: UUID, credential_type: str, credential_id: UUID):
    """Delete a credential"""
    if credential_type not in CREDENTIAL_MODELS:
        return jsonify({'error': 'Invalid credential type'}), 400
    
    model = CREDENTIAL_MODELS[credential_type]
    credential = db.session.get(model, credential_id)
    
    if not credential or credential.client_id != client_id:
        return jsonify({'error': 'Credential not found'}), 404
    
    try:
        db.session.delete(credential)
        db.session.commit()
        flash(f'{credential_type.title()} credential deleted successfully', 'success')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin.route('/client/<uuid:client_id>/credentials/view/<credential_type>/<uuid:credential_id>')
@admin_required
def view_credential(client_id: UUID, credential_type: str, credential_id: UUID):
    """View credential details (non-encrypted fields only)"""
    if credential_type not in CREDENTIAL_MODELS:
        flash('Invalid credential type', 'error')
        return redirect(url_for('admin.client_credentials', client_id=client_id))
    
    client = db.session.get(Client, client_id)
    if not client:
        flash('Client not found', 'error')
        return redirect(url_for('admin.index'))
    
    model = CREDENTIAL_MODELS[credential_type]
    credential = db.session.get(model, credential_id)
    
    if not credential or credential.client_id != client_id:
        flash('Credential not found', 'error')
        return redirect(url_for('admin.client_credentials', client_id=client_id))
    
    # Get viewable fields
    fields = {}
    for column in model.__table__.columns:
        if column.name not in ENCRYPTED_FIELDS:
            value = getattr(credential, column.name)
            fields[column.name] = value
    
    return render_template('admin/credentials/view.html',
                         client=client,
                         credential=credential,
                         credential_type=credential_type,
                         fields=fields)