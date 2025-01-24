from flask import redirect, url_for, session, request, Blueprint, current_app
from google_auth_oauthlib.flow import Flow
import os

gmail = Blueprint('gmail', __name__)
    
flow = Flow.from_client_secrets_file(
    client_secrets_file= current_app.config['CLIENT_SECRETS_FILE'],
    scopes=['https://www.googleapis.com/auth/gmail.modify'],
    # Temperaraly url for development only
    redirect_uri='http://localhost:5000/api/gmail/oauth2callback'
)

@gmail.route('/authorize')
def authorize():
    """Initiates OAuth flow by redirecting to Google's consent screen."""
    pass

@gmail.route('/oauth2callback')
def oauth2callback():
    """Handles OAuth callback, exchanges code for tokens."""
    pass