from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import Session
from .models import RapidAPICredentials
from standard_pipelines.extensions import db
from standard_pipelines.main.decorators import require_api_key
from standard_pipelines.data_flow.models import Client
from .. import api
from uuid import UUID


@api.route('/credentials/rapidapi/<client_id>', methods=['POST'])
@require_api_key
def create_rapidapi_credentials(client_id: UUID):
    """
    Create or update RapidAPI credentials for a client.
    
    Args:
        client_id: The UUID of the client
        
    Returns:
        JSON response with status message
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = {'rapidapi_key', 'rapidapi_host'}
        missing_fields = required_fields - data.keys()
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        # Check if credentials already exist
        existing_creds = RapidAPICredentials.query.filter_by(client_id=client_id).first()
        
        if existing_creds:
            # Update existing credentials
            existing_creds.rapidapi_key = data['rapidapi_key']
            existing_creds.rapidapi_host = data['rapidapi_host']
            db.session.commit()
            
            return jsonify({
                'message': 'RapidAPI credentials updated successfully',
                'id': str(existing_creds.id)
            }), 200
        else:
            # Create new credentials
            client = Client.query.get_or_404(client_id)
            
            credentials = RapidAPICredentials(
                client_id=client_id,
                rapidapi_key=data['rapidapi_key'],
                rapidapi_host=data['rapidapi_host']
            )
            
            credentials.client = client
            
            db.session.add(credentials)
            db.session.commit()
            
            return jsonify({
                'message': 'RapidAPI credentials created successfully',
                'id': str(credentials.id)
            }), 201
            
    except Exception as e:
        current_app.logger.error(f'Error creating RapidAPI credentials: {str(e)}')
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api.route('/credentials/rapidapi/<client_id>', methods=['GET'])
@require_api_key
def get_rapidapi_credentials(client_id: UUID):
    """
    Get RapidAPI credentials for a client.
    
    Args:
        client_id: The UUID of the client
        
    Returns:
        JSON response with credential information
    """
    try:
        credentials = RapidAPICredentials.query.filter_by(client_id=client_id).first()
        
        if not credentials:
            return jsonify({'error': 'RapidAPI credentials not found'}), 404
            
        return jsonify({
            'id': str(credentials.id),
            'client_id': str(credentials.client_id),
            'rapidapi_host': credentials.rapidapi_host,
            # Don't return the actual API key
            'has_api_key': True if credentials.rapidapi_key else False
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Error retrieving RapidAPI credentials: {str(e)}')
        return jsonify({'error': str(e)}), 500