from flask import Blueprint, jsonify, request, current_app, url_for, session, render_template
from standard_pipelines.auth.models import HubSpotCredentials
from flask_login import current_user, login_required
from standard_pipelines.auth.models import FirefliesCredentials, User, Role
from standard_pipelines.main.decorators import require_api_key
from standard_pipelines.data_flow.models import Client
from standard_pipelines.extensions import db
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from . import auth
from standard_pipelines.extensions import oauth
from flask_security.utils import hash_password
from functools import wraps
import secrets


@auth.route('/api/credentials/fireflies/<client_id>', methods=['GET', 'POST'])
def manage_fireflies_credentials(client_id: str):
    """Test endpoint to manage Fireflies credentials for a client."""
    try:
        client_uuid = UUID(client_id)
        client = Client.query.get_or_404(client_uuid)
        
        if request.method == 'POST':
            # Get API key from request
            data = request.get_json()
            if not data or 'api_key' not in data:
                return jsonify({'error': 'api_key is required'}), 400
                
            try:
                # Create and save new credentials
                credentials = FirefliesCredentials( # type: ignore
                    client_id=client_uuid, # type: ignore
                    api_key=data['api_key'] # type: ignore
                ) # type: ignore
                credentials.client = client
                credentials.save()
                
                return jsonify({
                    'message': 'Credentials saved successfully',
                    'client': client.name
                }), 201
                
            except IntegrityError:
                db.session.rollback()
                return jsonify({
                    'error': 'Credentials already exist for this client'
                }), 409
                
        else:  # GET request
            # Retrieve existing credentials
            new_credentials = FirefliesCredentials.query.filter_by(client_id=client_uuid).first()
            
            if not new_credentials:
                return jsonify({
                    'error': 'No credentials found for this client'
                }), 404
                
            return jsonify({
                'client': client.name,
                'api_key': new_credentials.api_key
            })
            
    except ValueError:
        return jsonify({'error': 'Invalid client ID format'}), 400 
    
# 3) Route to redirect the user to the HubSpot login/consent page
@auth.route('/oauth/login/hubspot')
@login_required
def login_hubspot():
    current_app.logger.info("Starting HubSpot OAuth login flow")
    
    # Log configuration values (but mask sensitive data)
    current_app.logger.debug(f"HubSpot Client ID: {current_app.config['HUBSPOT_CLIENT_ID'][:5]}...")
    if not current_app.config.get('HUBSPOT_CLIENT_ID'):
        current_app.logger.error("HUBSPOT_CLIENT_ID is not configured")
        return jsonify({'error': 'HubSpot client configuration is missing'}), 500
    
    if oauth.hubspot is None:
        current_app.logger.error("HubSpot OAuth client not initialized")
        return jsonify({'error': 'HubSpot OAuth client not initialized'}), 500
    
    # TODO: Change this to use the preffered URL scheme based on production or development
    redirect_uri = url_for('auth.authorize_hubspot', _external=True, _scheme='https')
    current_app.logger.debug(f"Generated redirect URI: {redirect_uri}")
    
    try:
        auth_redirect = oauth.hubspot.authorize_redirect(redirect_uri)
        current_app.logger.debug(f"Authorization URL generated successfully")
        return auth_redirect
    except Exception as e:
        current_app.logger.error(f"Error during HubSpot OAuth redirect: {str(e)}")
        return jsonify({'error': 'Failed to initiate OAuth flow'}), 500

# 4) Callback URL where HubSpot will redirect the user after they authorize
@auth.route('/oauth/authorize/hubspot')
@login_required
def authorize_hubspot():
    current_app.logger.info("Processing HubSpot OAuth callback")
    
    if oauth.hubspot is None:
        current_app.logger.error("HubSpot OAuth client not initialized")
        return jsonify({'error': 'HubSpot OAuth client not initialized'}), 500
        
    try:
        token = oauth.hubspot.authorize_access_token()
        current_app.logger.info("Successfully obtained HubSpot access token")
        current_app.logger.debug(f"Token expiry: {token.get('expires_at')}")
        
        # Get current user's client_id
        if not current_user or not current_user.is_authenticated:
            current_app.logger.error("No authenticated user found")
            return jsonify({'error': 'Authentication required'}), 401
            
        client_id = current_user.client_id
        client = Client.query.get_or_404(client_id)
        current_app.logger.debug(f"Found client: {client.name}")
        
        # Create or update HubSpot credentials
        try:
            # Check if credentials already exist
            existing_creds = HubSpotCredentials.query.filter_by(client_id=client_id).first()
            
            if existing_creds:
                current_app.logger.info(f"Updating existing HubSpot credentials for client {client.name}")
                existing_creds.hubspot_refresh_token = token['refresh_token']
                existing_creds.hubspot_access_token = token['access_token']
                existing_creds.hubspot_token_expiry = token.get('expires_at')
                existing_creds.save()
            else:
                current_app.logger.info(f"Creating new HubSpot credentials for client {client.name}")
                credentials = HubSpotCredentials(
                    client_id=client_id,
                    hubspot_client_id=current_app.config['HUBSPOT_CLIENT_ID'],
                    hubspot_client_secret=current_app.config['HUBSPOT_CLIENT_SECRET'],
                    hubspot_refresh_token=token['refresh_token']
                )
                credentials.client = client  # Attach the client object
                credentials.save()
                
            current_app.logger.info("Successfully stored HubSpot credentials in database")
            
            # Store minimal info in session for current request handling
            session['hubspot_connected'] = True
            
            return render_template(
                'auth/oauth_success.html',
                service='HubSpot',
                client_name=client.name
            )
            
        except Exception as e:
            current_app.logger.error(f"Error storing HubSpot credentials: {str(e)}")
            return jsonify({'error': 'Failed to store credentials'}), 500
        
    except Exception as e:
        current_app.logger.error(f"Error during HubSpot OAuth token exchange: {str(e)}")
        return jsonify({'error': 'Failed to complete OAuth flow'}), 500

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
@auth.route('/api/register', methods=['POST'])
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
        if current_app.user_datastore.find_user(email=data['email']):
            return jsonify({'error': 'User already exists'}), 409
            
        # Create the user using user_datastore
        try:
            user = current_app.user_datastore.create_user(
                email=data['email'],
                password=hash_password(data['password']),
                client=client,
                active=data.get('active', True),
                confirmed_at=db.func.now()  # Set confirmed_at to now since this is an admin creation
            )
            current_app.user_datastore.commit()
            
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