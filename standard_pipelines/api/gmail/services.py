from flask import current_app
from .models import GmailCredentials
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError
from standard_pipelines.extensions import db
import requests

class GmailService:
    def __init__(self, credentials):
        self.credentials = credentials

    def send_email(self, to_address, subject, body):
        pass

    #====== Helper functions ======#
    def refresh_access_token(self):
        try:
            missing_fields = [field for field in ['refresh_token', 'token_uri', 'oauth_client_id', 'oauth_client_secret'] if not getattr(self.credentials, field)]
            if missing_fields:
                current_app.logger.exception(f"A required field is missing: {', '.join(missing_fields)}")
                return {'error': f"A required field is missing: {', '.join(missing_fields)}"}

            payload = {
                'client_id': self.credentials.oauth_client_id,
                'client_secret': self.credentials.oauth_client_secret,
                'refresh_token': self.credentials.refresh_token,
                'grant_type': 'refresh_token'
            }

            response = requests.post(self.credentials.token_uri, data=payload)
            response.raise_for_status()

            token_data = response.json()
            if 'access_token' not in token_data:
                error_description = token_data.get('error_description', token_data.get('error', 'Unknown error'))
                current_app.logger.error(f"Failed to refresh token: {error_description}")
                return {'error': f"Failed to refresh token: {error_description}"}

            # Update the credentials with the new access token
            self.credentials.access_token = token_data['access_token']
            db.session.commit()

            current_app.logger.info("Access token refreshed successfully.")
            return {'access_token': token_data['access_token']}
        
        except requests.exceptions.HTTPError as http_err:
            # Need to handle the case where the refresh token is expired or invalid
            if response.status_code == 400 and 'invalid_grant' in response.json().get('error', ''):
                current_app.logger.error("Refresh token has expired or is invalid. User re-authorization required.")
                return {'error': 'Refresh token is expired or invalid. Please reauthorize.'}
            current_app.logger.error(f"HTTP error while refreshing token: {http_err}")
            return {'error': 'HTTP error occurred while refreshing token'}

        except requests.exceptions.RequestException as e:
            current_app.logger.exception(f"Failed to refresh access token: {e}")
            return {'error': 'Failed to refresh access token'}
        
        except Exception as e:
            current_app.logger.exception(f"Unexpected error while refreshing access token: {e}")
            return {'error': 'An unexpected error occurred while refreshing access token'}


    def structure_email_data(self, to_address, subject, body):
        pass


def get_user_credentials():
    try:
        user_id = current_user.id
        credentials = GmailCredentials.query.filter_by(user_id=user_id).first()
        if not credentials:
            current_app.logger.exception('No credentials found for the user')
            return {'error': 'No credentials found for the user'}
        return credentials
    
    except SQLAlchemyError as e:
        current_app.logger.exception(f'Database error occurred: {e}')
        return {'error': 'An error occurred while getting the user credentials'}
    
    except Exception as e:
        current_app.logger.exception(f'An unexpected error occurred: {e}')
        return {'error': 'An unexpected error occurred'}