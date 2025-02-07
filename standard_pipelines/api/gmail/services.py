from flask import current_app
from standard_pipelines.auth.models import GmailCredentials
from sqlalchemy.exc import SQLAlchemyError
from email.message import EmailMessage
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
import base64


class GmailService:
    def __init__(self):
        self.credentials = None
        self.client_id = None
        self.token_uri = "https://oauth2.googleapis.com/token"


    def send_email(self, to_address, subject, body):
        try:
            email_data = self.structure_email_data(to_address, subject, body)
            if 'error' in email_data:
                return email_data  

            google_credentials = Credentials(
                token = self.credentials.access_token,
                refresh_token = self.credentials.refresh_token,
                token_uri = self.token_uri,
                client_id = current_app.config['GMAIL_CLIENT_ID'],
                client_secret = current_app.config['GMAIL_CLIENT_SECRET'],
                scopes = current_app.config['GMAIL_SCOPES'].split()
            )

            # Create the Gmail service object
            service = build('gmail', 'v1', credentials=google_credentials)
            # Sends the email using the Gmail API
            message = service.users().messages().send(userId="me", body=email_data).execute()

            current_app.logger.info(f'Email sent successfully to {to_address} with message id: {message["id"]}')
            return {'message': 'Email sent successfully', 'message_id': message['id']}
        
        except HttpError as e:
            status_code = e.resp.status
            error_reason = e.reason

            current_app.logger.exception(f"HTTP error {status_code}: {error_reason}")
            return {'error': f'{error_reason}'}
            
        except RefreshError as e:
            current_app.logger.exception(f'Refresh error occurred: {str(e)}')
            return {'error': 'Refresh error occurred'}
    
        except Exception as e:
            current_app.logger.exception(f'An unexpected error occurred while sending email: {e}')
            return {'error': 'An unexpected error occurred while sending email'}

    #====== Helper functions ======#
    def structure_email_data(self, to_address, subject, body):
        try:            
            # Construct MIME message using EmailMessage class
            message = EmailMessage()
            message["To"] = to_address
            message["Subject"] = subject
            message.set_content(body)

            # Encode the MIME message in base64url format
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            return {"raw": raw_message}
    
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while structuring email data: {e}")
            return {'error': 'An unexpected error occurred while structuring email data'}
      
    def set_user_credentials(self, client_id : str):
        try:
            credentials = GmailCredentials.query.filter_by(client_id=client_id).first()
            if not credentials:
                current_app.logger.exception('No credentials found for the user')
                return {'error': 'No credentials found for the user'}
            
            self.credentials = credentials
            self.client_id = client_id
            return {'message': 'User credentials retrieved successfully'}
        
        except SQLAlchemyError as e:
            current_app.logger.exception(f'Database error occurred: {e}')
            return {'error': 'An error occurred while getting the user credentials'}
        
        except Exception as e:
            current_app.logger.exception(f'An unexpected error occurred: {e}')
            return {'error': 'An unexpected error occurred'}