from flask import redirect, url_for, session, request, current_app, flash, jsonify
from flask_login import current_user
from google_auth_oauthlib.flow import Flow
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from standard_pipelines.extensions import db
from standard_pipelines.api.gmail.models import GmailCredentials
from standard_pipelines.api.gmail.services import GmailService, get_user_credentials
from datetime import datetime, timezone, timedelta
from . import gmail

#============= Authorization ===============#

def get_flow():
    """Create and return a Flow object with the current app's configuration."""
    return Flow.from_client_secrets_file(
        client_secrets_file=current_app.config['CLIENT_SECRETS_FILE'],
        scopes=['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly'],
        redirect_uri=current_app.config['GMAIL_REDIRECT_URI']
    )

@gmail.route('/authorize')
def authorize():
    """Initiates OAuth flow by redirecting to Google's consent screen."""
    try:
        flow = get_flow()
        session['redirect_url'] = request.args.get('next') or request.referrer or url_for('main.index')

        authorization_url, state = flow.authorization_url(
            # Request offline access to get a refresh token
            access_type='offline',  
            # Lets the application request additional scopes without re-prompting the user
            include_granted_scopes='true'  
        )

        current_app.logger.info(f"Generated authorization URL: {authorization_url}")
        
        session['state'] = state
        
        return redirect(authorization_url)
    
    except HTTPException as e:
        current_app.logger.exception(f"HTTP error during authorization: {e}")
        flash('An error occurred while trying to authorize. Please try again.', 'error')
        next_url = session.pop('redirect_url', url_for('main.index'))
        return redirect(next_url)
    
    except Exception as e:
        current_app.logger.exception(f"Unexpected error during authorization: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')
        next_url = session.pop('redirect_url', url_for('main.index'))
        return redirect(next_url)

@gmail.route('/oauth2callback')
def oauth2callback():
    """Handles OAuth callback, exchanges code for tokens."""
    try:
        flow = get_flow()
        
        #The state verification is used to prevent CSRF attacks
        if 'state' not in session or session['state'] != request.args.get('state'):
            current_app.logger.exception(f'Invalid state parameter: Start: {session["state"]} End:{request.args.get("state")}')
            flash('An error occurred while authorizing', 'error')
            next_url = session.pop('redirect_url', url_for('main.index'))
            return redirect(next_url)

        flow.fetch_token(authorization_response=request.url)

        credentials = flow.credentials

        gmail_credentials = GmailCredentials(
            user_id=current_user.id,
            email_address="",
            access_token=credentials.token,
            expire_time=datetime.now(timezone.utc) + timedelta(minutes=55), #token expires in 1 hour, 5 minute buffer
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri,
            oauth_client_id=credentials.client_id,
            oauth_client_secret=credentials.client_secret,
            scopes=' '.join(credentials.scopes)
        )

        db.session.add(gmail_credentials)
        db.session.commit()
        current_app.logger.info(f'Credentials stored successfully for client: {gmail_credentials.client_id}')
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception(f'Error storing credentials: {e}')
        flash('An error occurred while authorizing', 'error')
        next_url = session.pop('redirect_url', url_for('main.index'))
        return redirect(next_url)

    except Exception as e:
        current_app.logger.exception(f'Unexpected error during OAuth callback: {e}')
        flash('An unexpected error occurred. Please try again later.', 'error')
        next_url = session.pop('redirect_url', url_for('main.index'))
        return redirect(next_url)

    current_app.logger.info(f'Client has been successfully authorized: {gmail_credentials.client_id}')
    flash('Successfully authorized', 'success')
    
    next_url = session.pop('redirect_url', url_for('main.index'))
    return redirect(next_url)

#============= Functionality ===============#
@gmail.route('/send_email', methods=['POST'])
def send_email():
    try:
        data = request.get_json()
        email_data = {'to_address' : data.get('to_address'),
                      'subject' : data.get('subject'),
                      'body' : data.get('body')}

        missing_fields = [field for field in email_data if not email_data[field]]
        if missing_fields:
            current_app.logger.exception(f'A required field is missing: {", ".join(missing_fields)}')
            return jsonify({'error': f'A required field is missing: {", ".join(missing_fields)}'}), 400
        
        incorrect_types = [field for field in email_data if not isinstance(email_data[field], str)]
        if incorrect_types:
            current_app.logger.exception(f'Incorrect data type for fields: {", ".join(incorrect_types)}')
            return jsonify({'error': f'Incorrect data type for fields: {", ".join(incorrect_types)}'}), 400

        credentials = get_user_credentials()
        if 'error' in credentials:
            current_app.logger.exception(f'An error occurred while getting the user credentials: {credentials["error"]}')
            return jsonify({'error': credentials['error']}), 400
        
        gmail_service = GmailService(credentials)

        email_response = gmail_service.send_email(email_data['to_address'], email_data['subject'], email_data['body'])
        if 'error' in email_response :
            current_app.logger.exception(f'An error occurred while sending the email: {email_response["error"]}')
            return jsonify({'error': email_response['error']}), 400

        current_app.logger.info(f'Email sent successfully to {email_data["to_address"]}')
        return jsonify({'message': 'Email sent successfully'}), 200
    
    except Exception as e:
        current_app.logger.exception(f'An error occurred by user {getattr(current_user, "id", "unknown")}: {e}')
        return jsonify({'error': 'An unknown error occurred while sending the email'}), 500

