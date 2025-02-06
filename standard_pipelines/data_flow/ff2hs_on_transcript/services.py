import datetime
import os
import typing as t
from typing import Optional
import uuid
from flask import current_app
from functools import cached_property
from hubspot.files import ApiException
from standard_pipelines.data_flow.exceptions import APIError

from sqlalchemy import UUID
from ..services import BaseDataFlow
from standard_pipelines.api.hubspot.services import HubSpotAPIManager
from standard_pipelines.api.fireflies.services import FirefliesAPIManager
from standard_pipelines.api.openai.services import OpenAIAPIManager
from ...auth.models import HubSpotCredentials, FirefliesCredentials, OpenAICredentials
from ..exceptions import InvalidWebhookError
from .models import FF2HSOnTranscriptConfiguration

class FF2HSOnTranscript(BaseDataFlow[FF2HSOnTranscriptConfiguration]):

    # Magic hubspot numbers to associate various object types
    # Don't change these unless you know what you're doing
    # Docs: https://developers.hubspot.com/docs/guides/api/crm/associations/associations-v4#association-type-id-values
    MEETING_TO_CONTACT_ASSOCIATION_ID = 200
    MEETING_TO_DEAL_ASSOCIATION_ID = 212
    NOTE_TO_DEAL_ASSOCIATION_ID = 214

    OPENAI_SUMMARY_MODEL = "gpt-4o"

    @classmethod
    def data_flow_name(cls) -> str:
        return "ff2hs_on_transcript"

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
        credentials = OpenAICredentials.query.filter_by(client_id=self.client_id).first()
        openai_config = {
            "api_key": credentials.openai_api_key
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

    # TODO: Want to change this, creating contacts in extract isn't really the right place
    def extract(self, context: t.Optional[dict] = None) -> dict:
        meeting_id = context["meeting_id"]
        transcript, emails, names = self.fireflies_api_manager.transcript(meeting_id)
        contacts = []

        # Contacts from emails
        for email in emails:
            try:
                resp = self.hubspot_api_manager.contact_by_name_or_email(email=email)
            except Exception:
            # <--    CHANGED: create contact if not found
                resp = self.hubspot_api_manager.create_contact(email=email)
            contacts.append(resp)

        # Contacts from names
        for name in names:
            try:
                resp = self.hubspot_api_manager.contact_by_name_or_email(name=name)
            except Exception:
                # Split name into first and last if it contains a space
                name_parts = name.split(maxsplit=1)
                if len(name_parts) > 1:
                    resp = self.hubspot_api_manager.create_contact(
                        first_name=name_parts[0],
                        last_name=name_parts[1]
                    )
                else:
                    resp = self.hubspot_api_manager.create_contact(first_name=name)
            contacts.append(resp)

        # TODO: Fix this deal shit
        deals = []
        for contact in contacts:
            try:
                resp = self.hubspot_api_manager.deal_by_contact_id(contact["id"])
            except Exception:
                # <-- CHANGED: create deal if not found
                # We'll build a simple deal name from the contact's email or first name
                contact_props = contact.get("properties", {})
                fallback_name = contact_props.get("email") or contact_props.get("firstname") or "Unnamed Contact"
                deal_name = f"Deal for {fallback_name}"
                # "appointmentscheduled" can be changed to your actual stage ID
                resp = self.hubspot_api_manager.create_deal(
                    deal_name=deal_name,
                    stage_id=self.configuration.intial_deal_stage_id,
                    contact_id=contact["id"]
                )
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

    # TODO: Fix this deal shit
    def transform(self, data: dict, context: t.Optional[dict] = None):
        # if len(data["deals"]) > 1:
        #     raise ValueError("More than one deal found")
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
