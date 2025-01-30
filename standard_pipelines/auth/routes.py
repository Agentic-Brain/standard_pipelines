from flask import Blueprint, jsonify, request, current_app, url_for, session, render_template
from standard_pipelines.auth.models import HubSpotCredentials
from flask_login import current_user
from standard_pipelines.auth.models import FirefliesCredentials
from standard_pipelines.data_flow.models import Client
from standard_pipelines.extensions import db
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from . import auth
from standard_pipelines.extensions import oauth


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
        
    redirect_uri = url_for('auth.authorize_hubspot', _external=True)
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
                # TODO: Make sure this works without manually attaching the client object
                current_app.logger.info(f"Updating existing HubSpot credentials for client {client.name}")
                existing_creds.hubspot_refresh_token = token['refresh_token']
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
            
        except Exception as e:
            current_app.logger.error(f"Error storing HubSpot credentials: {str(e)}")
            return jsonify({'error': 'Failed to store credentials'}), 500
        
        session['hubspot_token'] = token
        current_app.logger.info("Stored HubSpot token in session")
        
        return f"HubSpot OAuth successful!<br>Token Info: {token}"
        
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