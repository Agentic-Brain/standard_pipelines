# 3) Route to redirect the user to the Zoho login/consent page
import json
from typing import Optional
from standard_pipelines.auth import auth


from flask import current_app, jsonify, render_template, session, url_for
from flask_login import current_user, login_required

from standard_pipelines.api.zoho.models import ZohoCredentials
from standard_pipelines.data_flow.models import Client
from standard_pipelines.extensions import oauth
from .. import api


@api.route('/zoho/oauth/login')
@login_required
def login_zoho():
    current_app.logger.info("Starting Zoho OAuth login flow")

    # Log configuration values (but mask sensitive data)
    current_app.logger.debug(f"Zoho Client ID: {current_app.config['ZOHO_CLIENT_ID'][:5]}...")
    if not current_app.config.get('ZOHO_CLIENT_ID'):
        current_app.logger.error("ZOHO_CLIENT_ID is not configured")
        return jsonify({'error': 'Zoho client configuration is missing'}), 500

    if oauth.zoho is None:
        current_app.logger.error("Zoho OAuth client not initialized")
        return jsonify({'error': 'Zoho OAuth client not initialized'}), 500

    # TODO: Change this to use the preffered URL scheme based on production or development
    redirect_uri = url_for('api.authorize_zoho', _external=True)
    current_app.logger.debug(f"Generated redirect URI: {redirect_uri}")

    try:
        auth_redirect = oauth.zoho.authorize_redirect(redirect_uri, access_type='offline')
        current_app.logger.debug(f"Authorization URL generated successfully")
        return auth_redirect
    except ConnectionError as e:
        current_app.logger.exception("Error during Zoho OAuth redirect")
    return jsonify({'error': 'Failed to initiate OAuth flow'}), 500


# 4) Callback URL where Zoho will redirect the user after they authorize
@api.route('/zoho/oauth/authorize')
@login_required
def authorize_zoho():
    current_app.logger.info("Processing Zoho OAuth callback")

    if oauth.zoho is None:
        current_app.logger.error("Zoho OAuth client not initialized")
        return jsonify({'error': 'Zoho OAuth client not initialized'}), 500

    try:
        token = oauth.zoho.authorize_access_token()
        current_app.logger.info("Successfully obtained Zoho access token")
        current_app.logger.debug(f"Token expiry: {token.get('expires_at')}")
        current_app.logger.debug(f"Token: {json.dumps(token, indent=4)}")

        # Get current user's client_id
        if not current_user or not current_user.is_authenticated:
            current_app.logger.error("No authenticated user found")
            return jsonify({'error': 'Authentication required'}), 401

        client_id = current_user.client_id
        client = Client.query.get_or_404(client_id)
        current_app.logger.debug(f"Found client: {client.name}")

        # Create or update Zoho credentials
        try:
            # Check if credentials already exist
            existing_creds : Optional[ZohoCredentials] = ZohoCredentials.query.filter_by(client_id=client_id).first()

            credentials : ZohoCredentials = None
            if not existing_creds:
                current_app.logger.info(f"Creating new Zoho credentials for client {client.name}")
                credentials = ZohoCredentials(
                    client_id=client_id,
                    oauth_client_id=current_app.config['ZOHO_CLIENT_ID'],
                    oauth_client_secret=current_app.config['ZOHO_CLIENT_SECRET'],
                )
            else:
                current_app.logger.info(f"Updating existing Zoho credentials for client {client.name}")
                credentials = existing_creds

            credentials.client = client;
            credentials.oauth_refresh_token = token['refresh_token']
            credentials.oauth_access_token = token['access_token']
            credentials.oauth_expires_at = token.get('expires_at')
            credentials.save()

            current_app.logger.info("Successfully stored Zoho credentials in database")

            # Store minimal info in session for current request handling
            session['ZOHO_connected'] = True

            return render_template(
                'auth/oauth_success.html',
                service='Zoho',
                client_name=client.name
            )

        except Exception as e:
            current_app.logger.exception(f"Error storing Zoho credentials: {e}")
            return jsonify({'error': f'Failed to store credentials: {str(e)}'}), 500

    except Exception as e:
        current_app.logger.error(f"Error during Zoho OAuth token exchange: {str(e)}")
        return jsonify({'error': 'Failed to complete OAuth flow'}), 500