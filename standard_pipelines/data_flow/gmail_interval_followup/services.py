from ..services import BaseDataFlow
from .models import GmailIntervalFollowupConfiguration
from standard_pipelines.api.google.models import GoogleCredentials
from standard_pipelines.api.hubspot.models import HubSpotCredentials
from standard_pipelines.api.openai.models import OpenAICredentials
from standard_pipelines.api.hubspot.services import HubSpotAPIManager
from standard_pipelines.api.google.gmail_services import GmailAPIManager
from standard_pipelines.api.openai.services import OpenAIAPIManager
from standard_pipelines.api.fireflies.services import FirefliesAPIManager
from standard_pipelines.api.fireflies.models import FirefliesCredentials
from standard_pipelines.data_flow.exceptions import InvalidWebhookError
from functools import cached_property
from typing import Optional
import typing as t
import requests
from datetime import datetime, timedelta
from standard_pipelines.extensions import db
from .models import GmailIntervalFollowupSchedule

class GmailIntervalFollowup(BaseDataFlow[GmailIntervalFollowupConfiguration]):
    
    @classmethod
    def data_flow_name(cls) -> str:
        return "gmail_interval_followup"

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

    
    @cached_property
    def openai_api_manager(self) -> OpenAIAPIManager:
        credentials = OpenAICredentials.query.filter_by(client_id=self.client_id).first()
        openai_config = {
            "api_key": credentials.openai_api_key
        }
        return OpenAIAPIManager(openai_config)
    
    @cached_property
    def fireflies_api_manager(self) -> FirefliesAPIManager:
        credentials = FirefliesCredentials.query.filter_by(client_id=self.client_id).first()
        fireflies_config = {
            "api_key": credentials.fireflies_api_key
        }
        return FirefliesAPIManager(fireflies_config)
    
    def context_from_webhook_data(self, webhook_data: t.Any) -> t.Optional[dict]:
        if not isinstance(webhook_data, dict):
            raise InvalidWebhookError('Invalid webhook data')
        if webhook_data.get("eventType") != "Transcription completed":
            raise InvalidWebhookError('Webhook does not represent a completed transcription')
        meeting_id = webhook_data.get("meetingId")
        if not isinstance(meeting_id, str):
            raise InvalidWebhookError("Invalid meeting ID")
        return {
            "meeting_id": meeting_id
        }
    
    def extract(self, context: t.Optional[dict] = None) -> dict:
        if context is None or "meeting_id" not in context:
            raise ValueError("meeting_id is required in context")
            
        meeting_id = context["meeting_id"]
        transcript, emails, names, organizer_email = self.fireflies_api_manager.transcript(meeting_id) # type: ignore
        
            
        # Extract attendee information from the matching transcript
        fireflies_attendees = [
            {"name": name, "email": email}
            for name, email in zip(names, emails)
        ]

        # Only attendees that are not from our client's email domain should be
        # contacts in HubSpot.
        contactable_attendees = []
        for attendee in fireflies_attendees:
            if not attendee["email"].endswith(self.configuration.internal_domain):
                contactable_attendees.append(attendee)

        google_credentials = db.session.query(GoogleCredentials).filter(GoogleCredentials.user_email == organizer_email).first()
        
        if google_credentials is None:
            raise ValueError(f"No Google credentials found for organizer_email: {organizer_email}")

        return {
            "fireflies_transcript": transcript,
            "contactable_attendees": contactable_attendees,
            "organizer_email": organizer_email,
            "google_credentials": google_credentials
        }
        
    def transform(self, input_data: dict | None = None, context: dict | None = None):
        if input_data is None:
            raise ValueError("input_data is required")
        email_prompt = self.configuration.email_body_prompt.format(transcript=input_data["fireflies_transcript"])
        
        # TODO: Wrap this openapi call in try
        chat_completion = self.openai_api_manager.chat(email_prompt, model="gpt-4")
        email_body = chat_completion.choices[0].message.content  # Extract the actual text
        
        google_api_config = { 
            "refresh_token": input_data["google_credentials"].refresh_token
        }
        gmail_client = GmailAPIManager(google_api_config)
        draft_return = gmail_client.create_draft(input_data["contactable_attendees"], self.configuration.subject_line_template, email_body)
        return {
            'thread_id': draft_return['thread_id'],
            'original_transcript': input_data["fireflies_transcript"],
            'google_credentials': input_data["google_credentials"]
        }
    
    def load(self, input_data: dict | None = None, context: dict | None = None):
        if input_data is None:
            raise ValueError("input_data is required")
        
        next_scheduled_time = datetime.utcnow() + timedelta(days=self.configuration.email_interval_days)
        
        schedule = GmailIntervalFollowupSchedule(
            configuration_id=self.configuration.id, # type: ignore
            thread_id=input_data["thread_id"], # type: ignore
            gmail_credentials_id=input_data["google_credentials"].id, # type: ignore
            scheduled_time=next_scheduled_time, # type: ignore
            is_recurring=True, # type: ignore
            recurrence_interval=self.configuration.email_interval_days, # type: ignore
            max_runs=self.configuration.email_retries, # type: ignore
            original_transcript=input_data["original_transcript"] # type: ignore
        )

        schedule.save()
