from flask import current_app
from standard_pipelines.api.services import BaseAPIManager
from email.message import EmailMessage
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from email.utils import getaddresses
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

    def create_draft(self, to_address, subject, body, thread_id=None):
        """
        Creates a draft email in Gmail.

        Args:
            to_address (str or list): Recipient's email address(es).
            subject (str): Email subject.
            body (str): Email body content.
            thread_id (str, optional): The Gmail thread ID to associate the draft with.

        Returns:
            dict: Contains draft ID, thread ID, and status message on success,
                or an error message on failure.
        """
        try:
            current_app.logger.info(f'Creating draft email for {to_address}')
            email_data = self._structure_email_data(to_address, subject, body)
            if 'error' in email_data:
                return email_data

            # If a thread ID is provided, attach it to the message resource.
            if thread_id:
                email_data["threadId"] = thread_id

            # Create the draft using the Gmail API.
            draft = self.gmail_service.users().drafts().create(
                userId="me",
                body={'message': email_data}
            ).execute()

            # Get the thread ID from the created draft.
            created_thread_id = draft['message'].get('threadId')

            current_app.logger.info(f'Draft created successfully with id: {draft["id"]} in thread: {created_thread_id}')
            return {
                'message': 'Draft created successfully',
                'draft_id': draft['id'],
                'thread_id': created_thread_id
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

    def get_thread(self, thread_id: str):
        """
        Retrieves a Gmail thread (with its messages) given a thread ID.
        
        Args:
            thread_id (str): The Gmail thread ID.
            
        Returns:
            dict: The thread details as returned by the Gmail API.
        """
        try:
            thread = self.gmail_service.users().threads().get(userId="me", id=thread_id).execute()
            current_app.logger.info(f"Thread {thread_id} retrieved successfully.")
            return thread
        except HttpError as e:
            status_code = e.resp.status
            error_reason = e.reason
            current_app.logger.error(f"HTTP error {status_code} while retrieving thread {thread_id}: {error_reason}")
            return {'error': f'{error_reason}'}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while retrieving thread {thread_id}: {e}")
            return {'error': 'An unexpected error occurred while retrieving thread'}

    def get_to_addresses_from_thread(self, thread_id: str) -> list[str]:
        """
        Retrieves all unique email addresses from the 'To' header across all messages in a Gmail thread.
        
        Args:
            thread_id (str): The Gmail thread ID.
            
        Returns:
            list[str]: A list of unique email addresses found in the 'To' headers.
        """
        # Retrieve the thread data using your existing get_thread method.
        thread = self.get_thread(thread_id)
        if not thread or 'error' in thread:
            current_app.logger.error(f"Unable to retrieve thread {thread_id}")
            return []
        
        addresses = set()
        messages = thread.get('messages', [])
        
        for message in messages:
            headers = message.get('payload', {}).get('headers', [])
            for header in headers:
                if header.get('name', '').lower() == 'to':
                    # Use getaddresses to parse the header value, which may contain multiple emails.
                    parsed = getaddresses([header.get('value', '')])
                    for name, email in parsed:
                        if email:
                            addresses.add(email)
        
        return list(addresses)

    def has_recipient_responded(self, thread_id: str, sender_email: str) -> bool:
        """
        Checks whether any message in the thread indicates that the recipient has responded.
        
        Args:
            thread_id (str): The Gmail thread ID.
            recipient_email (str): The recipient's email address.
            sender_email (str): Your email address (i.e., the sender).
            
        Returns:
            bool: True if a response from the recipient is detected, False otherwise.
        """
        # Retrieve the thread details using your existing method.
        thread = self.get_thread(thread_id)
        if not thread or 'error' in thread:
            current_app.logger.error(f"Unable to retrieve thread {thread_id}")
            return False
        
        # Iterate over all messages in the thread.
        for message in thread.get('messages', []):
            # The headers are usually in the payload.
            headers = message.get('payload', {}).get('headers', [])
            for header in headers:
                if header.get('name', '').lower() == 'from':
                    from_value = header.get('value', '')
                    # If the "From" header includes the recipient's email, we assume they've replied.
                    if sender_email.lower() not in from_value.lower():
                        current_app.logger.info(f"Response detected from in thread {thread_id}")
                        return True
        return False

    #====== Helper functions ======#
    def _structure_email_data(self, to_address, subject, body):
        try:            
            # Construct MIME message using EmailMessage class
            message = EmailMessage()
            
            # Handle single string, list of strings, or list of dicts
            if isinstance(to_address, (list, tuple)):
                # Check if we have a list of dictionaries
                if to_address and isinstance(to_address[0], dict):
                    emails = [addr['email'] for addr in to_address if 'email' in addr]
                    message["To"] = ", ".join(emails)
                else:
                    # List of email strings
                    message["To"] = ", ".join(to_address)
            else:
                # Single email string
                message["To"] = to_address
                
            message["Subject"] = subject
            message.set_content(body)

            # Encode the MIME message in base64url format
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            return {"raw": raw_message}
    
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while structuring email data: {e}")
            return {'error': 'An unexpected error occurred while structuring email data'}

