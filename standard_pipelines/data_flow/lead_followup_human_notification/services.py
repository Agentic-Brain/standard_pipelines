from ..services import BaseDataFlow
from .models import LeadFollowupHumanNotificationConfiguration
from standard_pipelines.api.google.models import GoogleCredentials
from standard_pipelines.api.hubspot.models import HubSpotCredentials
from standard_pipelines.api.hubspot.services import HubSpotAPIManager
from standard_pipelines.api.google.gmail_services import GmailAPIManager
from standard_pipelines.data_flow.exceptions import InvalidWebhookError
from functools import cached_property
from typing import Optional
import typing as t
from flask import current_app


class LeadFollowupHumanNotification(BaseDataFlow[LeadFollowupHumanNotificationConfiguration]):
    
    @classmethod
    def data_flow_name(cls) -> str:
        return "lead_followup_human_notification"

    @cached_property
    def hubspot_api_manager(self) -> HubSpotAPIManager:
        credentials: Optional[HubSpotCredentials] = HubSpotCredentials.query.filter_by(client_id=self.client_id).first()
        if credentials is None:
            raise ValueError("No HubSpot credentials found for client")
        hubspot_config = {
            "client_id": credentials.hubspot_client_id,
            "client_secret": credentials.hubspot_client_secret,
            "refresh_token": credentials.hubspot_refresh_token
        }
        return HubSpotAPIManager(hubspot_config)
    
    def context_from_webhook_data(self, webhook_data: t.Any) -> t.Optional[dict]:
        """
        Process incoming webhook data to extract email, name, and transcript.
        
        Expected webhook data format:
        {
            "email": "user@example.com",
            "first_name": "First Name",
            "last_name": "Last Name"
            "transcript": "Meeting transcript content..."
        }
        """
        if not isinstance(webhook_data, dict):
            raise InvalidWebhookError('Invalid webhook data')
        
        email = webhook_data.get("email")
        first_name = webhook_data.get("first_name")
        last_name = webhook_data.get('last_name')
        transcript = webhook_data.get("transcript")
        
        if not email or not transcript:
            raise InvalidWebhookError('Email and transcript are required')
        
        return {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "transcript": transcript
        }
    
    def extract(self, context: t.Optional[dict] = None) -> dict:
        """
        Extract contact information from HubSpot based on email/name and get the associated owner.
        Also find the Google credentials for the sending email.
        """
        if context is None or "email" not in context:
            raise ValueError("Email is required in context")
        
        email = context["email"]
        first_name = context.get("first_name")
        last_name = context.get("last_name")
        transcript = context["transcript"]
        
        # Find the contact in HubSpot
        try:
            # First get contact ID through name or email
            if first_name and last_name:
                name = ' '.join([first_name, last_name])
            contact_basic = self.hubspot_api_manager.contact_by_name_or_email(name=name, email=email)
            current_app.logger.info(f"Found contact in HubSpot: {contact_basic['id']}")
            
            # Get the contact with owner property explicitly included
            contact = self.hubspot_api_manager.contact_by_contact_id(
                contact_basic['id'], 
                properties=["hubspot_owner_id", "firstname", "lastname", "email"]
            )
            current_app.logger.info(f"Retrieved contact with properties: {contact.get('properties')}")
            
            # Get the owner directly from the contact
            owner_id = contact.get('properties', {}).get('hubspot_owner_id')
            current_app.logger.info(f"Contact owner ID: {owner_id}")
            
            if not owner_id:
                current_app.logger.warning(f"No owner found for contact {contact['id']}")
                owner_email = "acpohl21@gmail.com"  # Fallback if no owner
            else:
                # Get owner details
                owner_email = None
                all_owners = self.hubspot_api_manager.all_owners()
                for owner in all_owners:
                    if owner.get('id') == owner_id:
                        owner_email = owner.get('email')
                        break
                        
                if not owner_email:
                    current_app.logger.warning(f"Owner email not found for owner ID {owner_id}")
                    owner_email = "acpohl21@gmail.com"  # Fallback if owner has no email
            
            # Get Google credentials for sending email
            google_credentials = GoogleCredentials.query.filter_by(
                client_id=self.client_id,
                user_email=self.configuration.source_email
            ).first()
            
            if not google_credentials:
                raise ValueError(f"No Google credentials found for sending email {self.configuration.source_email}")
            
            return {
                "contact": contact,
                "owner_email": owner_email,
                "transcript": transcript,
                "google_credentials": google_credentials
            }
            
        except Exception as e:
            current_app.logger.error(f"Error extracting data: {str(e)}")
            raise
    
    def transform(self, input_data: dict | None = None, context: dict | None = None) -> dict:
        """
        Prepare email content using the transcript and contact information.
        """
        if input_data is None:
            raise ValueError("input_data is required")
        
        contact = input_data["contact"]
        owner_email = input_data["owner_email"]
        transcript = input_data["transcript"]
        google_credentials = input_data["google_credentials"]
        
        # Extract contact name from properties
        contact_first_name = contact.get("properties", {}).get("firstname", "")
        contact_last_name = contact.get("properties", {}).get("lastname", "")
        contact_full_name = f"{contact_first_name} {contact_last_name}".strip()
        
        # Create a simple email body with the transcript
        email_subject = "User has requested human followup"
        email_body = f"""Hello {owner_email},

{contact_full_name} has requested to contact a human. Details are below
"""
        
        return {
            "owner_email": owner_email,
            "email_subject": email_subject,
            "email_body": email_body,
            "google_credentials": google_credentials
        }
    
    def load(self, output_data: dict | None = None, context: dict | None = None) -> None:
        """
        Send the email using GmailAPIManager.
        """
        if output_data is None:
            raise ValueError("output_data is required")
        
        owner_email = output_data["owner_email"]
        email_subject = output_data["email_subject"]
        email_body = output_data["email_body"]
        google_credentials = output_data["google_credentials"]
        
        # Initialize Gmail client
        google_api_config = {
            "refresh_token": google_credentials.refresh_token
        }
        gmail_client = GmailAPIManager(google_api_config)
        
        # Get CC addresses if configured
        cc_addresses = self.configuration.cc_addresses if hasattr(self.configuration, 'cc_addresses') else None
        if cc_addresses:
            current_app.logger.info(f"Will CC emails to: {cc_addresses}")
        
        # Send the email
        current_app.logger.info(f"Sending email to {owner_email}")
        result = gmail_client.send_email(owner_email, email_subject, email_body, cc_addresses=cc_addresses)
        
        if 'error' in result:
            current_app.logger.error(f"Error sending email: {result['error']}")
            raise ValueError(f"Failed to send email: {result['error']}")
            
        current_app.logger.info(f"Email sent successfully with message ID: {result.get('message_id')}")