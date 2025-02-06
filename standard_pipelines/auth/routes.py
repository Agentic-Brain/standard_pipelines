from flask import Blueprint, jsonify, request, current_app, render_template
from standard_pipelines.main.decorators import require_api_key
from standard_pipelines.data_flow.models import Client
from standard_pipelines.extensions import db
from uuid import UUID
from . import auth
from standard_pipelines.extensions import oauth
from flask_security.utils import hash_password
from functools import wraps
import secrets


@auth.route('/oauth')
def oauth_index():
    """Index page showing all available OAuth login options."""
    current_app.logger.debug("Rendering OAuth index page")
    
    # Service-specific information
    oauth_service_info = {
        'hubspot': {
            'icon': 'https://www.hubspot.com/hubfs/HubSpot_Logos/HubSpot-Inversed-Favicon.png',
            'description': 'Connect to HubSpot CRM'
        }
        # Add other services here as they're implemented
    }
    
    return render_template(
        'auth/oauth_index.html',
        oauth=oauth,
        oauth_service_info=oauth_service_info
    )

# TODO: Remove upon creation of admin dash    
@auth.route('/manual/register', methods=['POST'])
@require_api_key
def register_user():
    """Protected endpoint to register a new user."""
    current_app.logger.info("Processing user registration request")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Validate required fields
        required_fields = ['email', 'password', 'client_id']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
            
        # Validate and get client
        try:
            client_uuid = UUID(data['client_id'])
            client = Client.query.get(client_uuid)
            if not client:
                return jsonify({'error': 'Invalid client_id'}), 404
        except ValueError:
            return jsonify({'error': 'Invalid client_id format'}), 400
            
        # Check if user already exists
        if current_app.user_datastore.find_user(email=data['email']): #type: ignore
            return jsonify({'error': 'User already exists'}), 409
            
        # Create the user using user_datastore
        try:
            user = current_app.user_datastore.create_user( #type: ignore
                email=data['email'],
                password=hash_password(data['password']),
                client=client,
                active=data.get('active', True),
                confirmed_at=db.func.now()  # Set confirmed_at to now since this is an admin creation
            )
            current_app.user_datastore.commit() #type: ignore
            
            current_app.logger.info(f"Successfully created user: {user.email}")
            
            return jsonify({
                'message': 'User created successfully',
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'client': client.name
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating user: {str(e)}")
            return jsonify({'error': 'Failed to create user'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error processing registration request: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500