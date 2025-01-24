from flask import current_app
from .models import GmailCredentials
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError


class GmailService:
    def __init__(self, credentials):
        self.credentials = credentials

    def send_email(self, to_address, subject, body):
        pass

    def refresh_access_token(self):
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