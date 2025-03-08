import datetime
import itertools
import json
import os
import typing as t
from typing import Optional, Any
import uuid
from flask import current_app
from functools import cached_property

from ...api.dialpad.models import DialpadCredentials

from ...api.zoho.models import ZohoCredentials

from ...api.dialpad.services import DialpadAPIManager
from ...api.zoho.services import ZohoAPIManager
from standard_pipelines.data_flow.exceptions import APIError

from sqlalchemy import UUID
from ..services import BaseDataFlow
from ...api.openai.services import OpenAIAPIManager
from ...api.openai.models import OpenAICredentials
from ..exceptions import InvalidWebhookError
from .models import Dialpad2ZohoOnTranscriptConfiguration

class Dialpad2ZohoOnTranscript(BaseDataFlow[Dialpad2ZohoOnTranscriptConfiguration]):

    OPENAI_SUMMARY_MODEL = "gpt-4o"

    @classmethod
    def data_flow_name(cls) -> str:
        return "dialpad2zoho_on_transcript"

    @cached_property
    def zoho_api_manager(self) -> ZohoAPIManager:
        credentials: Optional[ZohoCredentials] = ZohoCredentials.query.filter_by(client_id=self.client_id).first()
        if credentials is None:
            raise ValueError("No Zoho credentials found for client")

        return ZohoAPIManager(credentials)

    @cached_property
    def dialpad_api_manager(self) -> DialpadAPIManager:
        credentials = DialpadCredentials.query.filter_by(client_id=self.client_id).first()

        if not credentials:
            raise ValueError(f"No Dialpad credentials found for client {self.client_id}")
        dialpad_config = {
            "api_key": credentials.dialpad_api_key,
        }
        return DialpadAPIManager(dialpad_config)
    
    @cached_property
    def openai_api_manager(self) -> OpenAIAPIManager:
        credentials = OpenAICredentials.query.filter_by(client_id=self.client_id).first()
        if not credentials:
            raise ValueError(f"No OpenAI credentials found for client {self.client_id}")
        
        openai_config = {
            "api_key": credentials.openai_api_key
        }
        return OpenAIAPIManager(openai_config)

    def context_from_webhook_data(self, webhook_data: t.Any) -> t.Optional[dict]:
        if not isinstance(webhook_data, dict):
            raise InvalidWebhookError(f"Expected 'webhook_data' to be a dict, got type {type(webhook_data)}. Value: {webhook_data}")
        if webhook_data.get("state") != "hangup":
            raise InvalidWebhookError('Webhook does not represent a call hangup')
        call_id = webhook_data.get("call_id")
        if not isinstance(call_id, int):
            raise InvalidWebhookError("Invalid call ID")
        return {
            "call_id": call_id
        }

    def meeting_summary(self, transcript: str) -> str:
        prompt = self.configuration.prompt.format(transcript=transcript)
        return self.openai_api_manager.chat(prompt, model=self.OPENAI_SUMMARY_MODEL).choices[0].message.content

    def formatted_names(self, contacts: t.Iterable) -> str:
        names = [f"{contact.zoho_object_dict['properties']['firstname']} {contact.zoho_object_dict['properties']['lastname']}" for contact in contacts]
        if len(names) == 0:
            return "Unnamed Contact"
        if len(names) <= 3:
            return ", ".join(name for name in names)
        else:
            return f"{names[0]} et al."

    def zoho_contact(self, attendee_dict: dict[str, dict]):
        """Docs: https://developers.hubspot.com/docs/guides/api/crm/objects/contacts"""
        if attendee_dict.get("email") is None:
            raise ValueError("Email is required for a contact")

        if attendee_dict.get("name") is None:
            first_name = attendee_dict.get("email", "").split('@')[0]
            last_name = ""
        else:
            first_name, last_name = attendee_dict.get("name", "").split(" ", maxsplit=1)

        attendee_dict = {
            "properties": {
                "email": attendee_dict.get("email"),
                "firstname": first_name,
                "lastname": last_name,
                # "phone": "",
                # "company": "",
                # "website": "",
                # "lifecyclestage": ""
            }
        }

        return attendee_dict

    def zoho_deal(self, contact_names: str):
        deal_dict = {
            "properties": {
                # "amount": "",
                # "closedate": "",
                "dealname": f"Deal for {contact_names}",
                "pipeline": "default",
                "dealstage": self.configuration.initial_deal_stage_id,
            }
        }

        return deal_dict

    def zoho_meeting(self, transcript: str, contact_names: str) -> dict:
        """
        Docs: https://developers.hubspot.com/docs/guides/api/crm/engagements/meetings
        """
        now = datetime.datetime.now()
        meeting_name = f"Meeting with {contact_names}"

        if len(transcript) > 65535:
            current_app.logger.warning(f"Transcript too long. Truncating to 65535 characters.")
            current_app.logger.debug(f"Transcript too long. Truncating to 65535 characters. Transcript: {transcript}")
            transcript = transcript[:65535]

        meeting_dict = {
            "properties": {
                "hs_timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "hs_meeting_title": meeting_name,
                "hs_meeting_body": meeting_name,
                "hs_internal_meeting_notes": transcript,
                "hs_meeting_location": "Remote",
                "hs_meeting_start_time": now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                # "hs_meeting_end_time": "",
                "hs_meeting_outcome": "COMPLETED"
            }
        }

        return meeting_dict

    def zoho_note(self, transcript: str):
        now = datetime.datetime.now()
        meeting_summary = self.meeting_summary(transcript)[:65535]
        if len(meeting_summary) > 65535: # TODO: upload as file attachment if too long
            current_app.logger.warning(f"Meeting summary too long. Truncating to 65535 characters.")
            current_app.logger.debug(f"Meeting summary too long. Truncating to 65535 characters. Meeting summary: {meeting_summary}")
            meeting_summary = meeting_summary[:65535]
        
        note_dict = {
            "properties": {
                "hs_timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "hs_note_body": meeting_summary,
                # "hs_attachment_ids": ""
            }
        }

        return note_dict

    # TODO: Verify if this needs to work for multiple attendees in the call
    def extract(self, context: t.Optional[dict] = None) -> dict:
        if not context:
            raise ValueError("No call ID provided")
        call_id = context["call_id"]
        transcript_dict: dict[str, Any] = self.dialpad_api_manager.get_transcript(call_id)
        transcript = transcript_dict["transcript"]
        participants = transcript_dict["participants"]

        # Assuming first participant is host, second is guest
        return {
            "transcript": transcript,
            "guest": participants.get("guest"),
            "host": participants.get("host"),
        }

    def transform(self, data: dict, context: t.Optional[dict] = None):
        transcript = data["transcript"]
        guest = data["guest"]
        host = data["host"]
        contacts = []
        deals = []

        current_app.logger.debug(f"Transcript: {transcript}")
        current_app.logger.debug(f"Guest: {guest}")
        current_app.logger.debug(f"Host: {host}")

        try:
            name = guest['name']
            email = guest['email']
            if email:
                current_app.logger.warning(f"Guest has no email: {json.dumps(guest)}")
                contact = self.zoho_api_manager.get_contact_by_email(email=email)
            else:
                contact = self.zoho_api_manager.get
            if not contact:
                current_app.logger.warning(f"Contact not found for attendee {email}, creating one")
                contact = self.zoho_api_manager.create_contact(guest)

            current_app.logger.debug(f"Contact: {json.dumps(contact, indent=4)}")

            contacts.append(contact)
        except APIError:
            contacts.append(self.zoho_contact(guest))
        for contact in contacts:
            contact_id = contact.zoho_object_dict["id"]
            resp = self.zoho_api_manager.get_deal_by_contact_id(contact_id)
            deal_id = resp["id"]
            deal = self.zoho_api_manager.get_deal_by_deal_id(deal_id, properties=["zoho_owner_id"])
            deals.append(deal, self.zoho_api_manager)

        if len(contacts) > 0:
            formatted_names = self.formatted_names(contacts)

        if len(deals) > 1: # TODO: deduplicate the same deal found from different contacts
            warning_msg = f"Too many deals found for {formatted_names}."
            current_app.logger.warning(warning_msg)
        deal = deals[0] if len(deals) > 0 else self.zoho_api_manager.zoho_deal(formatted_names)

        user = self.zoho_api_manager.get_user_by_email(organizer_email)
        deal.add_owner_from_user(user)

        meeting = self.zoho_meeting(transcript, formatted_names)
        note = self.zoho_note(transcript)

        return {
            "contacts": contacts,
            "deal": deal,
            "meeting": meeting,
            "note": note,
        }

    def load(self, data: dict, context: t.Optional[dict] = None):
        contacts: list = data["contacts"]
        deal = data["deal"]
        meeting = data["meeting"]
        note = data["note"]

        evaluated_contacts = [contact.evaluate() for contact in contacts]
        for contact in evaluated_contacts:
            deal.add_association(contact)
            meeting.add_association(contact)

        evaluated_deal = deal.evaluate()

        meeting.add_association(evaluated_deal)
        meeting.add_owner_from_deal(evaluated_deal)
        meeting.evaluate()

        note.add_association(evaluated_deal)
        note.add_owner_from_deal(evaluated_deal)
        note.evaluate()
