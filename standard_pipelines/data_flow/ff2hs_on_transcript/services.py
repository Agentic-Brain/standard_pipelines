import datetime
import os
import typing as t
from typing import Optional
import uuid
from flask import current_app
from functools import cached_property

from sqlalchemy import UUID
from ..services import BaseDataFlow
from ..utils import HubSpotAPIManager, FirefliesAPIManager, OpenAIAPIManager
from ...auth.models import HubSpotCredentials, FirefliesCredentials
from ..exceptions import InvalidWebhookError
from .models import FF2HSOnTranscriptConfiguration

class FF2HSOnTranscript(BaseDataFlow[FF2HSOnTranscriptConfiguration]):

    # Magic hubspot numbers to associate various object types
    # Don't change these unless you know what you're doing
    MEETING_TO_CONTACT_ASSOCIATION_ID = 200
    MEETING_TO_DEAL_ASSOCIATION_ID = 212
    NOTE_TO_DEAL_ASSOCIATION_ID = 214
    OPENAI_SUMMARY_MODEL = "gpt-4o"

    @classmethod
    def data_flow_id(cls) -> uuid.UUID:
        return uuid.UUID("a1abd672-4e54-4ce7-8504-1625ea6f79aa")

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
    def fireflies_api_manager(self) -> FirefliesAPIManager:
        credentials = FirefliesCredentials.query.filter_by(client_id=self.client_id).first()
        fireflies_config = {
            "api_key": credentials.fireflies_api_key
        }
        return FirefliesAPIManager(fireflies_config)
    
    @cached_property
    def openai_api_manager(self) -> OpenAIAPIManager:
        # TODO: read credentials from the database
        openai_config = {
            "api_key": os.getenv("DEVELOPMENT_OPENAI_API_KEY")
        }
        return OpenAIAPIManager(openai_config)

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
        meeting_id = context["meeting_id"]
        transcript, emails, names = self.fireflies_api_manager.transcript(meeting_id)
        contacts = []
        for email in emails:
            resp = self.hubspot_api_manager.contact_by_name_or_email(email=email)
            contacts.append(resp)
        for name in names:
            resp = self.hubspot_api_manager.contact_by_name_or_email(name=name)
            contacts.append(resp)
        deals = []
        for contact in contacts:
            resp = self.hubspot_api_manager.deal_by_contact_id(contact["id"])
            id = resp["id"]
            resp = self.hubspot_api_manager.deal_by_deal_id(id, properties=["hubspot_owner_id"])
            deals.append(resp)
        return {
            "transcript": transcript,
            "contacts": contacts,
            "deals": deals
        }

    def meeting_summary(self, transcript: str) -> str:
        prompt = self.configuration.prompt.format(transcript=transcript)
        return self.openai_api_manager.chat(prompt, model=self.OPENAI_SUMMARY_MODEL).choices[0].message.content

    def hubspot_association_object(self, to_id: str, type_category: str, type_id: str) -> dict:
        return {
            "to": {
                "id": to_id
            },
            "types": [
                {
                    "associationCategory": type_category,
                    "associationTypeId": type_id
                }
            ]
        }

    def hubspot_meeting_object(self, transcript: str, contacts: list[dict], deal: dict) -> dict:
        now = datetime.datetime.now()
        contact_names = [contact["properties"]["firstname"] + " " + contact["properties"]["lastname"] for contact in contacts]
        contact_names_str = ", ".join(contact_names)
        
        return {
            "properties": {
                "hs_timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "hubspot_owner_id": deal["properties"]["hubspot_owner_id"],
                "hs_meeting_title": "Meeting with " + contact_names_str,
                "hs_meeting_body": "Meeting with " + contact_names_str,
                "hs_internal_meeting_notes": transcript,
                "hs_meeting_location": "Remote",
                "hs_meeting_start_time": now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                # "hs_meeting_end_time": "",
                "hs_meeting_outcome": "COMPLETED"
            },
            "associations": [
                *[self.hubspot_association_object(contact["id"], "HUBSPOT_DEFINED", self.MEETING_TO_CONTACT_ASSOCIATION_ID) for contact in contacts],
                self.hubspot_association_object(deal["id"], "HUBSPOT_DEFINED", self.MEETING_TO_DEAL_ASSOCIATION_ID)
            ]
        }

    def hubspot_note_object(self, transcript: str, contacts: list[dict], deal: dict) -> dict:
        now = datetime.datetime.now()

        return {
            "properties": {
                "hs_timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "hs_note_body": self.meeting_summary(transcript),
                "hubspot_owner_id": deal["properties"]["hubspot_owner_id"],
                # "hs_attachment_ids": ""
            },
            "associations": [
                self.hubspot_association_object(deal["id"], "HUBSPOT_DEFINED", self.NOTE_TO_DEAL_ASSOCIATION_ID)
            ]
        }

    def transform(self, data: dict, context: t.Optional[dict] = None):
        if len(data["deals"]) > 1:
            raise ValueError("More than one deal found")
        deal = data["deals"][0]
        meeting = self.hubspot_meeting_object(data["transcript"], data["contacts"], deal)
        note = self.hubspot_note_object(data["transcript"], data["contacts"], deal)
        return {
            "meeting": meeting,
            "note": note,
        }

    def load(self, data: dict, context: t.Optional[dict] = None):
        self.hubspot_api_manager.create_meeting(data["meeting"])
        self.hubspot_api_manager.create_note(data["note"])