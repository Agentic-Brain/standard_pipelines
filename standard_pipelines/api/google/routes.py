from flask import url_for, current_app, jsonify, render_template, session
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError
from standard_pipelines.extensions import db
from standard_pipelines.api.google.models import GoogleCredentials, GoogleCredentials
from standard_pipelines.data_flow.models import Client
from standard_pipelines.extensions import oauth
from authlib.integrations.base_client.errors import OAuthError
from standard_pipelines.api import api


@api.route('/google/oauth/login')
@login_required
def login_google():
    """Initiates OAuth flow by redirecting to Google's consent screen."""
    try:
        current_app.logger.info("Starting Google OAuth login flow")

        if oauth.google is None:
            current_app.logger.error("Google OAuth client not initialized")
            return jsonify({'error': 'Google OAuth client not initialized'}), 500

        redirect_uri = url_for('api.authorize_google', _external=True)
        current_app.logger.debug(f"Generated redirect URI: {redirect_uri}")

        auth_redirect = oauth.google.authorize_redirect(
            redirect_uri,
            access_type='offline',
            prompt='consent'
            )
        current_app.logger.debug(f"Authorization URL generated successfully")
        return auth_redirect
     
    except (OAuthError, ConnectionError) as e:
        current_app.logger.error(f"Error during Google OAuth redirect: {e}")
        return jsonify({'error': 'Failed to initiate OAuth flow'}), 500
    except Exception as e:
        current_app.logger.exception(f"Error during Google OAuth redirect: {e}")
        return jsonify({'error': f'Unexpected error during authorization'}), 500

@api.route('/google/oauth/authorize')
@login_required
def authorize_google():
    """Handles OAuth callback, exchanges code for tokens."""
    try:
        current_app.logger.info("Handling Google OAuth callback")
        
        if oauth.google is None:
            current_app.logger.error("Google OAuth client not initialized")
            return jsonify({'error': 'Google OAuth client not initialized'}), 500
        
        token = oauth.google.authorize_access_token()
        if not token:
            return jsonify({'error': 'Failed to retrieve access token'}), 400
        current_app.logger.info("Successfully obtained Google access token")
        current_app.logger.debug(f"Token expiry: {token.get('expires_at')}")

        # #Verify that the current user is avaliable and authenticated
        if not current_user or not current_user.is_authenticated:
            current_app.logger.error("No authenticated user found")
            return jsonify({'error': 'Authentication required'}), 401

        client_id = current_user.client_id
        client = Client.query.get_or_404(client_id)
        current_app.logger.debug(f"Found client: {client.name}")

        # Create or update Google credentials
        existing_credentials = GoogleCredentials.query.filter_by(client_id=client.id).first()
        if existing_credentials:
            existing_credentials.refresh_token = token['refresh_token']
            existing_credentials.save()  
            current_app.logger.info(f'Updated existing credentials for client')
        else:
            google_credentials = GoogleCredentials(
                client_id=client_id,
                refresh_token=token['refresh_token'],
            )
            google_credentials.client = client
            google_credentials.save()  
            current_app.logger.info(f'Created new credentials for client')
        
        current_app.logger.info("Successfully stored Google credentials in database")

        return render_template(
                'auth/oauth_success.html',
                service='Google',
                client_name=client.name
            )

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        return jsonify({'error': f'Error storing credentials: {e}'}), 500
    except OAuthError as e:
        current_app.logger.error(f"OAuth error: {e}")
        return jsonify({'error': 'OAuth authorization failed'}), 400
    except Exception as e:
        current_app.logger.exception(f"Unexpected error during OAuth callback: {e}")
        return jsonify({'error': f'Unexpected error during OAuth callback: {e}'}), 500