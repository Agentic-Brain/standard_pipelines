from flask import current_app, session
from .models import GmailCredentials
from standard_pipelines.auth.models import User
from sqlalchemy.exc import SQLAlchemyError
from standard_pipelines.extensions import db
import requests
from email.message import EmailMessage
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from datetime import datetime, timezone, timedelta
import base64


class GmailService:
    def __init__(self, credentials, client_id):
        self.credentials = credentials
        self.client_id = client_id
        self.email_address = ""

    def send_email(self, to_address, subject, body):
        try:
            # Checks if the access token is expired and refreshes it if so
            if self.credentials.get_expire_time_as_datetime() < datetime.now(timezone.utc):
                refresh_response = self.refresh_access_token()
                if 'error' in refresh_response:
                    return refresh_response

            # Sets the email address if it has not been set before
            if self.email_address == "":
                from_address = self.set_user_email()
                if 'error' in from_address:
                    return from_address

            email_data = self.structure_email_data(to_address, self.credentials.email_address, subject, body)
            if 'error' in email_data:
                return email_data  

            google_credentials = Credentials(
                token=self.credentials.access_token,
                refresh_token=self.credentials.refresh_token,
                token_uri=self.credentials.token_uri,
                client_id=self.credentials.oauth_client_id,
                client_secret=self.credentials.oauth_client_secret,
                scopes=self.credentials.scopes.split()
            )

            # Create the Gmail service object
            service = build('gmail', 'v1', credentials=google_credentials)
            # Sends the email using the Gmail API
            message = service.users().messages().send(userId="me", body=email_data).execute()

            current_app.logger.info(f'Email sent successfully to {to_address}')
            return {'message': 'Email sent successfully', 'message_id': message['id']}
        
        except HttpError as e:
            current_app.logger.exception(f'An error occurred while sending the email: {e}')
            return {'error': f'Failed to send email: {str(e)}'}
    
        except Exception as e:
            current_app.logger.exception(f'An unexpected error occurred while sending email: {e}')
            return {'error': 'An unexpected error occurred while sending email'}

    #====== Helper functions ======#
    def refresh_access_token(self):
        try:
            missing_fields = [field for field in ['refresh_token', 'token_uri', 'oauth_client_id', 'oauth_client_secret'] if not hasattr(self.credentials, field)]
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
                #Temporary error code check
                error_description = token_data.get('error_description', token_data.get('error', 'Unknown error'))
                current_app.logger.exception(f"Failed to refresh token: {error_description}")
                return {'error': f"Failed to refresh token: {error_description}"}

            self.credentials.access_token = token_data['access_token']
            self.credentials.expire_time = self.credentials.set_expire_time_from_datetime(datetime.now(timezone.utc) + timedelta(minutes=55))
            db.session.commit()

            current_app.logger.info("Access token refreshed successfully.")
            return {'message': 'Access token refreshed successfully'}
        
        except requests.exceptions.HTTPError as http_err:
            # Need to handle the case where the refresh token is expired or invalid
            if response.status_code == 400 and 'invalid_grant' in response.json().get('error', ''):
                current_app.logger.exception("Refresh token has expired or is invalid. User re-authorization required.")
                return {'error': 'Refresh token is expired or invalid. Please reauthorize.'}
            current_app.logger.exception(f"HTTP error while refreshing token: {http_err}")
            return {'error': 'HTTP error occurred while refreshing token'}

        except requests.exceptions.RequestException as e:
            current_app.logger.exception(f"Failed to refresh access token: {e}")
            return {'error': 'Failed to refresh access token'}
        
        except Exception as e:
            current_app.logger.exception(f"Unexpected error while refreshing access token: {e}")
            return {'error': 'An unexpected error occurred while refreshing access token'}

    def structure_email_data(self, to_address, from_address, subject, body):
        try:            
            # Construct MIME message using EmailMessage class
            message = EmailMessage()
            message["To"] = to_address
            message["From"] = from_address
            message["Subject"] = subject
            message.set_content(body)

            # Encode the MIME message in base64url format
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            return {"raw": raw_message}
    
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while structuring email data: {e}")
            return {'error': 'An unexpected error occurred while structuring email data'}
        
    def set_user_email(self):
        try:
            user_credentials = User.query.filter_by(client_id=self.client_id).first()
            email_address = user_credentials.email

            if email_address is None:
                current_app.logger.exception('No email address found in user profile')
                return {'error': 'No email address found in user profile'}

            self.credentials.email_address = email_address
            return {'message': 'User email address set successfully'}

        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while getting user email: {e}")
            return {'error': 'An unexpected error occurred while getting user email'}



def get_user_credentials(client_id : str):
    try:
        credentials = GmailCredentials.query.filter_by(client_id=client_id).first()
        if not credentials:
            current_app.logger.exception('No credentials found for the user')
            return {'error': 'No credentials found for the user'}
        return {'credentials': credentials}
    
    except SQLAlchemyError as e:
        current_app.logger.exception(f'Database error occurred: {e}')
        return {'error': 'An error occurred while getting the user credentials'}
    
    except Exception as e:
        current_app.logger.exception(f'An unexpected error occurred: {e}')
        return {'error': 'An unexpected error occurred'}