import asyncio

import requests
from flask import url_for, current_app, jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError
from authlib.integrations.base_client.errors import OAuthError
from msgraph import GraphServiceClient

from standard_pipelines.extensions import db
from standard_pipelines.data_flow.models import Client
from standard_pipelines.extensions import oauth
from standard_pipelines.api import api
from .token_credential import AccessTokenCredential
from .models import MicrosoftCredentials


@api.route('/microsoft/oauth/login')
@login_required
def login_microsoft():
    """Initiates OAuth flow by redirecting to Microsofts's consent screen."""
    try:
        current_app.logger.info("Starting Microsoft OAuth login flow")

        if oauth.microsoft is None:
            current_app.logger.error("Microsoft OAuth client not initialized")
            return jsonify({'error': 'Microsoft OAuth client not initialized'}), 500

        # Generate the URL to our own authorize endpoint
        # "api.authorize_microsoft" referrs to the function associated with the route
        redirect_uri = url_for('api.authorize_microsoft', _external=True, _scheme=current_app.config['PREFERRED_URL_SCHEME'])

        current_app.logger.debug(f"Generated redirect URL: {redirect_uri}")
        auth_redirect = oauth.microsoft.authorize_redirect(redirect_uri)
        current_app.logger.debug(f"Authorization URL generated successfully")

        return auth_redirect

    except (OAuthError, ConnectionError) as e:
        current_app.logger.error(f"Error during Microsoft OAuth redirect: {e}")
        return jsonify({'error': 'Failed to initiate OAuth flow'}), 500

    except Exception as e:
        current_app.logger.exception(f"Error during Microsoft OAuth redirect: {e}")
        return jsonify({'error': f'Unexpected error during authorization'}), 500


@api.route('/microsoft/oauth/authorize')
@login_required
def authorize_microsoft():
    """Handles OAuth callback, exchanges code for tokens."""
    try:
        current_app.logger.info("Handling Microsoft OAuth callback")

        if oauth.microsoft is None:
            current_app.logger.error("Microsoft OAuth client not initialized")
            return jsonify({'error': 'Microsoft OAuth client not initialized'}), 500

        token = oauth.microsoft.authorize_access_token()
        if not token:
            current_app.logger.error("Failed to obtain access token from Microsoft")
            return jsonify({'error': 'Failed to retrieve access token'}), 400

        current_app.logger.info("Successfully obtained Microsoft access token")
        current_app.logger.debug(f"Token expiry: {token.get('expires_at')}")

        # Verify that the current user is available and authenticated
        if not current_user or not current_user.is_authenticated:
            current_app.logger.error("No authenticated user found")
            return jsonify({'error': 'Authentication required'}), 401

        # "client" is the current user
        client_id = current_user.client_id
        client = Client.query.get_or_404(client_id)

        current_app.logger.info(f"Processing authorization for client: {client.name} (ID: {client_id})")

        user_email = None
        user_name = None
        try:
            current_app.logger.debug("Fetching user info from Microsoft graph API")

            api_credentials = AccessTokenCredential(token["access_token"], token.get("expires_at")) # token["refresh_token"]
            # To initialize graph_client, see https://learn.microsoft.com/en-us/graph/sdks/create-client?from=snippets&tabs=python
            graph_client = GraphServiceClient(api_credentials, ["User.Read"])
            async def fn():
                return await graph_client.me.get()
            results = asyncio.run(fn())

            user_email = results.mail
            user_name = results.display_name

            current_app.logger.info(f"Successfully fetched user info for: {user_email} ({user_name})")
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
        existing_credentials = MicrosoftCredentials.query.filter_by(
            client_id=client_id,
            user_email=user_email
        ).first()

        try:
            if existing_credentials:
                current_app.logger.info(f"Found existing credentials for {user_email}, updating...")
                existing_credentials.access_token = token['access_token']
                existing_credentials.refresh_token = token['refresh_token']
                existing_credentials.expires_at = token.get("expires_at")
                existing_credentials.user_name = user_name
                existing_credentials.save()
                current_app.logger.info(f"Successfully updated credentials for email: {user_email}")
            else:
                current_app.logger.info(f"No existing credentials found for {user_email}, creating new entry...")
                credentials = MicrosoftCredentials(
                    client_id=client_id,
                    access_token=token['access_token'],
                    refresh_token=token['refresh_token'],
                    expires_at=token.get("expires_at"),
                    user_email=user_email or "",
                    user_name=user_name
                )
                credentials.client = client
                credentials.save()
                current_app.logger.info(f"Successfully created new credentials for email: {user_email}")

        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error while saving credentials: {str(e)}")
            db.session.rollback()
            raise

        current_app.logger.info(f"Microsoft OAuth flow completed successfully for {user_email}")

        return render_template(
                'auth/oauth_success.html',
                service='Microsoft',
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