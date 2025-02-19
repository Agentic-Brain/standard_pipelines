from flask import current_app
from standard_pipelines.api.services import BaseAPIManager
from email.message import EmailMessage
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import base64


class GmailAPIManager(BaseAPIManager):
    def __init__(self, api_config: dict) -> None:
        super().__init__(api_config)
        self.google_credentials = Credentials(
                token = None,
                refresh_token = api_config['refresh_token'],
                token_uri = "https://oauth2.googleapis.com/token",
                client_id = current_app.config['GOOGLE_CLIENT_ID'],
                client_secret = current_app.config['GOOGLE_CLIENT_SECRET'],
                scopes = current_app.config['GOOGLE_SCOPES'].split()
            )
        self.gmail_service = build('gmail', 'v1', credentials=self.google_credentials)

    @property
    def required_config(self) -> list[str]:
        return ['refresh_token']
    
    @property
    def refresh_token(self):
        """Attempts to refresh the access token using the stored refresh token."""
        try:
            self.google_credentials.refresh(Request())
        except RefreshError as e:
            current_app.logger.error(f"Token refresh failed: {str(e)}")
            #Can be used to detect if the refresh token has been revoked or is invalid and handle it
            if "invalid_grant" in str(e):
                current_app.logger.error("The refresh token has been revoked or is invalid.")
                raise RefreshError("The refresh token has been revoked or is invalid.")
            else:
                current_app.logger.error(f"An error occurred during token refresh: {str(e)}")
                raise RefreshError(f"An error occurred during token refresh: {str(e)}")
        except Exception as e:
            current_app.logger.error(f"Unknown error during token refresh: {str(e)}")
            raise RefreshError(f"Unknown error during token refresh: {str(e)}")

    #====== Gmail API functions ======#
    def send_email(self, to_address, subject, body):
        try:
            current_app.logger.info(f'Sending email to {to_address}')
            email_data = self._structure_email_data(to_address, subject, body)
            if 'error' in email_data:
                return email_data  

            # Create the Gmail service object
            # Sends the email using the Gmail API
            message = self.gmail_service.users().messages().send(userId="me", body=email_data).execute()

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

    def create_draft(self, to_address, subject, body):
        """
        Creates a draft email in Gmail.
        
        Args:
            to_address (str or list): Recipient's email address(es)
            subject (str): Email subject
            body (str): Email body content
            
        Returns:
            dict: Contains draft ID, thread ID, and status message on success, or error message on failure
        """
        try:
            current_app.logger.info(f'Creating draft email for {to_address}')
            email_data = self._structure_email_data(to_address, subject, body)
            if 'error' in email_data:
                return email_data

            # Create the draft using Gmail API
            draft = self.gmail_service.users().drafts().create(
                userId="me",
                body={'message': email_data}
            ).execute()

            # Get the thread ID from the draft message
            thread_id = draft['message']['threadId']

            current_app.logger.info(f'Draft created successfully with id: {draft["id"]} in thread: {thread_id}')
            return {
                'message': 'Draft created successfully',
                'draft_id': draft['id'],
                'thread_id': thread_id
            }

        except HttpError as e:
            status_code = e.resp.status
            error_reason = e.reason
            current_app.logger.error(f"HTTP error {status_code}: {error_reason}")
            return {'error': f'{error_reason}'}
            
        except RefreshError as e:
            current_app.logger.error(f'Refresh error occurred: {str(e)}')
            return {'error': 'Refresh error occurred'}
    
        except Exception as e:
            current_app.logger.exception(f'An unexpected error occurred while creating draft: {e}')
            return {'error': 'An unexpected error occurred while creating draft'}

    #====== Helper functions ======#
    def _structure_email_data(self, to_address, subject, body):
        try:            
            # Construct MIME message using EmailMessage class
            message = EmailMessage()
            
            # Handle either single email or list of emails
            if isinstance(to_address, (list, tuple)):
                message["To"] = ", ".join(to_address)
            else:
                message["To"] = to_address
                
            message["Subject"] = subject
            message.set_content(body)

            # Encode the MIME message in base64url format
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            return {"raw": raw_message}
    
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while structuring email data: {e}")
            return {'error': 'An unexpected error occurred while structuring email data'}

