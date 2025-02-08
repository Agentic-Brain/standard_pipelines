from flask import redirect, url_for, session, request, current_app, flash, jsonify, json
from google_auth_oauthlib.flow import Flow
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from standard_pipelines.extensions import db
from standard_pipelines.auth.models import GmailCredentials
from standard_pipelines.data_flow.models import Client
import urllib.parse
from standard_pipelines.auth import auth
import os

#============= Routes ===============#
@auth.route('/oauth/login/gmail/<client_id>')
def authorize(client_id: str):
    """Initiates OAuth flow by redirecting to Google's consent screen."""
    try:
        if current_app.config['ENV'] in ['development', 'testing']:
            os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

        redirect_url = request.args.get('next') or request.referrer or url_for('main.index')

        client = Client.query.get_or_404(client_id)

        flow = get_flow()
        
        passed_data = {
            'client_id': str(client.id),
            'redirect_url': redirect_url
            }
        serialized_data = urllib.parse.quote(json.dumps(passed_data))

        authorization_url, state = flow.authorization_url(
            # Request offline access to get a refresh token
            access_type='offline',  
            # Lets the application request additional scopes without re-prompting the user
            include_granted_scopes='true',
            prompt='consent',
            state=serialized_data
        )

        session['state'] = state
        current_app.logger.info(f"Generated authorization URL: {authorization_url}")
        
        return redirect(authorization_url)
    
    except HTTPException as e:
        return display_error_and_redirect(redirect_url, f"HTTP error during authorization: {e}")
    except ValueError as e:
        return display_error_and_redirect(redirect_url, f"Value error during authorization: {e}")
    except Exception as e:
        return display_error_and_redirect(redirect_url, f"Unexpected error during authorization: {e}")

@auth.route('/oauth/authorize/gmail')
def oauth2callback():
    """Handles OAuth callback, exchanges code for tokens."""
    try:
        decoded_data = {}
        flow = get_flow()

        serialized_data = request.args.get('state')
        if serialized_data is None:
            return display_error_and_redirect(url_for('main.index'), 'State parameter is missing from request from Google')
        decoded_data = json.loads(urllib.parse.unquote(serialized_data))
        
        required_fields = {'client_id', 'redirect_url'}
        missing_fields = required_fields - decoded_data.keys()
        if missing_fields:
            return display_error_and_redirect(decoded_data.get('redirect_url', url_for('main.index')), f'Missing required fields: {", ".join(missing_fields)}')
        
        #The state verification is used to prevent CSRF attacks
        if 'state' not in session or session['state'] != serialized_data:
            return display_error_and_redirect(decoded_data.get('redirect_url', url_for('main.index')), f'Invalid state parameter: Start: {session["state"]} End:{request.args.get("state")}')

        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials

        client = Client.query.get_or_404(decoded_data['client_id'])

        existing_credentials = GmailCredentials.query.filter_by(client_id=client.id).first()
        if existing_credentials:
            existing_credentials.access_token = credentials.token
            existing_credentials.refresh_token = credentials.refresh_token
            existing_credentials.save()  
            current_app.logger.info(f'Updated existing credentials for client')
        else:
            gmail_credentials = GmailCredentials(
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
            )
            gmail_credentials.client = client
            gmail_credentials.save()  
            current_app.logger.info(f'Created new credentials for client')
        
        next_url = decoded_data.get('redirect_url', url_for('main.index'))
        current_app.logger.info(f'Client has been successfully authorized')
        flash('Successfully authorized', 'success')
        return redirect(next_url)
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return display_error_and_redirect(decoded_data.get('redirect_url', url_for('main.index')), f'Error storing credentials: {e}')

    except Exception as e:
        return display_error_and_redirect(decoded_data.get('redirect_url', url_for('main.index')), f'Unexpected error during OAuth callback: {e}')

#============= Helper Functions ===============#
def get_flow():
    """Create and return a Flow object with the current app's configuration."""
    try:
        client_config = {
            "installed": {
                "client_id": current_app.config['GMAIL_CLIENT_ID'],
                "project_id": current_app.config['GMAIL_PROJECT_ID'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": current_app.config['GMAIL_CLIENT_SECRET'],
                "redirect_uris": current_app.config['GMAIL_REDIRECT_URI']
            }
        }
        return Flow.from_client_config(
            client_config=client_config,
            scopes=current_app.config['GMAIL_SCOPES'].split(),
            redirect_uri=current_app.config['GMAIL_REDIRECT_URI']
        )

    except ValueError as e:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, description=f"An unexpected error occurred while creating the OAuth flow: {e}")

def display_error_and_redirect(redirect_url : str, debug_message : str, flash_message : str = "An error occurred while trying to authorize."):
    current_app.logger.exception(debug_message)
    flash(flash_message)
    next_url = redirect_url or url_for('main.index')
    return redirect(next_url)
