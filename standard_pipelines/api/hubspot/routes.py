# 3) Route to redirect the user to the HubSpot login/consent page
from standard_pipelines.auth import auth


from flask import current_app, jsonify, render_template, session, url_for
from flask_login import current_user, login_required

from standard_pipelines.api.hubspot.models import HubSpotCredentials
from standard_pipelines.data_flow.models import Client
from standard_pipelines.extensions import oauth
from .. import api


@api.route('/hubspot/oauth/login')
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
    redirect_uri = url_for('api.authorize_hubspot', _external=True)
    current_app.logger.debug(f"Generated redirect URI: {redirect_uri}")

    try:
        auth_redirect = oauth.hubspot.authorize_redirect(redirect_uri)
        current_app.logger.debug(f"Authorization URL generated successfully")
        return auth_redirect
    except ConnectionError as e:
        current_app.logger.exception("Error during HubSpot OAuth redirect")
    return jsonify({'error': 'Failed to initiate OAuth flow'}), 500


# 4) Callback URL where HubSpot will redirect the user after they authorize
@api.route('/hubspot/oauth/authorize')
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