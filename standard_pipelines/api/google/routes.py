from flask import url_for, current_app, jsonify, render_template, session
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError
import requests
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

        redirect_uri = url_for('api.authorize_google', _external=True, _scheme=current_app.config['PREFERRED_URL_SCHEME'])
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
            current_app.logger.error("Failed to obtain access token from Google")
            return jsonify({'error': 'Failed to retrieve access token'}), 400

        current_app.logger.info("Successfully obtained Google access token")
        current_app.logger.debug(f"Token expiry: {token.get('expires_at')}")

        # Verify that the current user is available and authenticated
        if not current_user or not current_user.is_authenticated:
            current_app.logger.error("No authenticated user found")
            return jsonify({'error': 'Authentication required'}), 401

        client_id = current_user.client_id
        client = Client.query.get_or_404(client_id)
        current_app.logger.info(f"Processing authorization for client: {client.name} (ID: {client_id})")

        user_email = None
        user_name = None
        try:
            USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
            current_app.logger.debug("Fetching user info from Google API")
            headers = {"Authorization": f"Bearer {token['access_token']}"}
            response = requests.get(USER_INFO_URL, headers=headers)
            response.raise_for_status()  # Raise exception for non-200 status codes
            userinfo = response.json()
            user_email = userinfo['email']
            user_name = userinfo['name']
            current_app.logger.info(f"Successfully fetched user info for: {user_email}")
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Request failed when fetching user info: {str(e)}")
            return jsonify({'error': 'Failed to fetch user info'}), 400
        except KeyError as e:
            current_app.logger.error(f"Missing expected field in user info response: {str(e)}")
            return jsonify({'error': 'Invalid user info response'}), 400
        except Exception as e:
            current_app.logger.error(f"Error fetching user info: {str(e)}")
            return jsonify({'error': 'Failed to fetch user info'}), 400

        # Check for existing credentials with same email
        current_app.logger.debug(f"Checking for existing credentials for email: {user_email}")
        existing_credentials = GoogleCredentials.query.filter_by(
            client_id=client.id, 
            user_email=user_email
        ).first()

        try:
            if existing_credentials:
                current_app.logger.info(f"Found existing credentials for {user_email}, updating...")
                existing_credentials.refresh_token = token['refresh_token']
                existing_credentials.user_name = user_name
                existing_credentials.save()
                current_app.logger.info(f"Successfully updated credentials for email: {user_email}")
            else:
                current_app.logger.info(f"No existing credentials found for {user_email}, creating new entry...")
                google_credentials = GoogleCredentials(
                    client_id=client_id,
                    refresh_token=token['refresh_token'],
                    user_email=user_email,
                    user_name=user_name
                )
                google_credentials.client = client
                google_credentials.save()
                current_app.logger.info(f"Successfully created new credentials for email: {user_email}")

        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error while saving credentials: {str(e)}")
            db.session.rollback()
            raise

        current_app.logger.info(f"Google OAuth flow completed successfully for {user_email}")

        return render_template(
                'auth/oauth_success.html',
                service='Google',
                client_name=client.name
            )

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {str(e)}")
        return jsonify({'error': f'Error storing credentials: {str(e)}'}), 500
    except OAuthError as e:
        current_app.logger.error(f"OAuth error: {str(e)}")
        return jsonify({'error': 'OAuth authorization failed'}), 400
    except Exception as e:
        current_app.logger.exception(f"Unexpected error during OAuth callback: {str(e)}")
        return jsonify({'error': f'Unexpected error during OAuth callback: {str(e)}'}), 500