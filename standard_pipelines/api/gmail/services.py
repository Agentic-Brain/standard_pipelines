from flask import current_app
from standard_pipelines.api.services import BaseAPIManager
from standard_pipelines.auth.models import GmailCredentials
from sqlalchemy.exc import SQLAlchemyError
from email.message import EmailMessage
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
import base64


class GmailService(BaseAPIManager):
    def __init__(self, api_config: dict, credentials: GmailCredentials) -> None:
        super().__init__(api_config)
        self.user_db_credentials = credentials
        self.google_credentials = Credentials(
                token = self.user_db_credentials.access_token,
                refresh_token = self.user_db_credentials.refresh_token,
                token_uri = "https://oauth2.googleapis.com/token",
                client_id = self.api_config['GMAIL_CLIENT_ID'],
                client_secret = self.api_config['GMAIL_CLIENT_SECRET'],
                scopes = self.api_config['GMAIL_SCOPES'].split()
            )

    @property
    def required_config(self) -> list[str]:
        return ['GMAIL_CLIENT_ID', 'GMAIL_CLIENT_SECRET', 'GMAIL_SCOPES']
    
    def send_email(self, to_address, subject, body):
        try:
            current_app.logger.info(f'Sending email to {to_address}')
            email_data = self.structure_email_data(to_address, subject, body)
            if 'error' in email_data:
                return email_data  

            # Create the Gmail service object
            service = build('gmail', 'v1', credentials=self.google_credentials)
            # Sends the email using the Gmail API
            message = service.users().messages().send(userId="me", body=email_data).execute()

            current_app.logger.info(f'Email sent successfully to {to_address} with message id: {message["id"]}')
            return {'message': 'Email sent successfully', 'message_id': message['id']}
        
        except HttpError as e:
            status_code = e.resp.status
            error_reason = e.reason

            current_app.logger.error(f"HTTP error {status_code}: {error_reason}")
            return {'error': f'{error_reason}'}
            
        except RefreshError as e:
            current_app.logger.error(f'Refresh error occurred: {str(e)}')
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