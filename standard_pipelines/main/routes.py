from flask import request, jsonify, current_app, render_template, url_for
from standard_pipelines.api.fireflies.models import FirefliesCredentials
from standard_pipelines.api.hubspot.models import HubSpotCredentials
from standard_pipelines.api.openai.models import OpenAICredentials
from standard_pipelines.main.decorators import require_api_key
from standard_pipelines.data_flow.models import Client
from standard_pipelines.auth.models import AnthropicCredentials
from standard_pipelines.extensions import db
from uuid import UUID
from . import main


@main.route('/status')
@require_api_key
def test():
    return "Test endpoint active" 

# TODO: Once we have a proper key loading system we should move these to the testing routes

@main.route('/credentials/hubspot', methods=['POST'])
@require_api_key
def create_hubspot_credentials():
    try:
        data = request.get_json()
        
        # Validate required fields using set operations
        required_fields = {'client_id', 'hubspot_client_id', 'hubspot_client_secret', 'hubspot_refresh_token'}
        missing_fields = required_fields - data.keys()
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        # Create new credentials
        credentials = HubSpotCredentials(
            client_id=data['client_id'],
            hubspot_client_id=data['hubspot_client_id'],
            hubspot_client_secret=data['hubspot_client_secret'],
            hubspot_refresh_token=data['hubspot_refresh_token']
        )
        
        client = Client.query.get_or_404(data['client_id'])
        credentials.client = client
        
        db.session.add(credentials)
        db.session.commit()
        
        return jsonify({
            'message': 'HubSpot credentials created successfully',
            'id': str(credentials.id)
        }), 201
        
    except Exception as e:
        current_app.logger.error(f'Error creating HubSpot credentials: {str(e)}')
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main.route('/credentials/hubspot/<uuid:client_id>', methods=['GET'])
@require_api_key
def get_hubspot_credentials(client_id: UUID):
    try:
        credentials = HubSpotCredentials.query.filter_by(client_id=client_id).first()
        if not credentials:
            return jsonify({'error': 'Credentials not found'}), 404
            
        return jsonify({
            'id': str(credentials.id),
            'client_id': str(credentials.client_id),
            'hubspot_client_id': credentials.hubspot_client_id,
            'hubspot_client_secret': credentials.hubspot_client_secret,
            'hubspot_refresh_token': credentials.hubspot_refresh_token,
            # Not returning sensitive fields like client_secret and refresh_token
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Error retrieving HubSpot credentials: {str(e)}')
        return jsonify({'error': str(e)}), 500

@main.route('/credentials/fireflies', methods=['POST'])
@require_api_key
def create_fireflies_credentials():
    try:
        data = request.get_json()
        
        # Validate required fields using set operations
        required_fields = {'client_id', 'fireflies_api_key'}
        missing_fields = required_fields - data.keys()
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        # Create new credentials
        credentials = FirefliesCredentials(
            client_id=UUID(data['client_id']),
            fireflies_api_key=data['fireflies_api_key']
        )
        
        client = Client.query.get_or_404(data['client_id'])
        credentials.client = client
        
        db.session.add(credentials)
        db.session.commit()
        
        return jsonify({
            'message': 'Fireflies credentials created successfully',
            'id': str(credentials.id)
        }), 201
        
    except Exception as e:
        current_app.logger.error(f'Error creating Fireflies credentials: {str(e)}')
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main.route('/credentials/fireflies/<uuid:client_id>', methods=['GET'])
@require_api_key
def get_fireflies_credentials(client_id: UUID):
    try:
        credentials = FirefliesCredentials.query.filter_by(client_id=client_id).first()
        if not credentials:
            return jsonify({'error': 'Credentials not found'}), 404
            
        return jsonify({
            'id': str(credentials.id),
            'client_id': str(credentials.client_id),
            'fireflies_api_key': credentials.fireflies_api_key
            # Not returning sensitive field fireflies_api_key
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Error retrieving Fireflies credentials: {str(e)}')
        return jsonify({'error': str(e)}), 500
        
    
@main.route('/credentials/anthropic', methods=['POST'])
@require_api_key
def create_anthropic_credentials():
    try:
        data = request.get_json()
        
        # Validate required fields using set operations
        required_fields = {'client_id', 'anthropic_api_key'}
        missing_fields = required_fields - data.keys()
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        # Create new credentials
        credentials = AnthropicCredentials(
            client_id=data['client_id'],
            anthropic_api_key=data['anthropic_api_key']
        )
        
        client = Client.query.get_or_404(data['client_id'])
        credentials.client = client
        
        db.session.add(credentials)
        db.session.commit()
        
        return jsonify({
            'message': 'Anthropic credentials created successfully',
            'id': str(credentials.id)
        }), 201
        
    except Exception as e:
        current_app.logger.error(f'Error creating Anthropic credentials: {str(e)}')
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
       
       
@main.route('/log')
def log():
    return render_template('log.html') 
        
@main.route('/oauth-portal')
def oauth_portal():
    """Serve the OAuth portal page"""
    # Build the oauth_services dictionary similar to auth/routes.py
    # TODO: Want to change this thing
    oauth_services = {
        'hubspot': {
            'enabled': bool(current_app.config.get('USE_HUBSPOT')),
            'connected': False,  # Would use current_user.client_id if login_required
            'icon': url_for('static', filename='img/oauth/hubspot.svg'),
            'description': 'Connect to HubSpot to sync contacts and deals'
        },
        'google': {
            'enabled': bool(current_app.config.get('USE_GOOGLE')),
            'connected': False,
            'icon': url_for('static', filename='img/oauth/google.svg'),
            'description': 'Connect to Google for email integration'
        },
        'zoho': {
            'enabled': bool(current_app.config.get('USE_ZOHO')),
            'connected': False,
            'icon': url_for('static', filename='img/oauth/zoho.svg'),
            'description': 'Connect to Zoho to sync contacts and deals'
        }
    }
    
    return render_template('oauth.html', oauth_services=oauth_services)