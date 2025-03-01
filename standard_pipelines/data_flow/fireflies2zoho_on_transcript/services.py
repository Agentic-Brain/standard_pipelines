import datetime
import itertools
import os
import typing as t
from typing import Optional
import uuid
from flask import current_app
from functools import cached_property
from zoho.files import ApiException

from ...api.fireflies.models import FirefliesCredentials

from ...api.zoho.models import ZohoCredentials

from ...api.fireflies.services import FirefliesAPIManager
from ...api.zoho.services import (
    ZohoAPIManager,
    ExtantContactZohoObject,
    ExtantDealZohoObject,
    ExtantUserZohoObject,
    CreatableContactZohoObject,
    CreatableDealZohoObject,
    CreatableMeetingZohoObject,
    CreatableNoteZohoObject,
)
from standard_pipelines.data_flow.exceptions import APIError

from sqlalchemy import UUID
from ..services import BaseDataFlow
from ...api.openai.services import OpenAIAPIManager
from ...api.openai.models import OpenAICredentials
from ..exceptions import InvalidWebhookError
from .models import Fireflies2ZohoOnTranscriptConfiguration

class Fireflies2ZohoOnTranscript(BaseDataFlow[Fireflies2ZohoOnTranscriptConfiguration]):

    OPENAI_SUMMARY_MODEL = "gpt-4o"

    @classmethod
    def data_flow_name(cls) -> str:
        return "fireflies2zoho_on_transcript"

    @cached_property
    def zoho_api_manager(self) -> ZohoAPIManager:
        credentials: Optional[ZohoCredentials] = ZohoCredentials.query.filter_by(client_id=self.client_id).first()
        if credentials is None:
            raise ValueError("No HubSpot credentials found for client")
        zoho_config = {
            "client_id": credentials.zoho_client_id,
            "client_secret": credentials.zoho_client_secret,
            "refresh_token": credentials.zoho_refresh_token
        }
        return ZohoAPIManager(zoho_config)

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

    def meeting_summary(self, transcript: str) -> str:
        prompt = self.configuration.prompt.format(transcript=transcript)
        return self.openai_api_manager.chat(prompt, model=self.OPENAI_SUMMARY_MODEL).choices[0].message.content

    def formatted_names(self, contacts: t.Iterable[CreatableContactZohoObject | ExtantContactZohoObject]) -> str:
        names = [f"{contact.zoho_object_dict['properties']['firstname']} {contact.zoho_object_dict['properties']['lastname']}" for contact in contacts]
        if len(names) == 0:
            return "Unnamed Contact"
        if len(names) <= 3:
            return ", ".join(name for name in names)
        else:
            return f"{names[0]} et al."

    def zoho_contact(self, attendee_dict: dict[str, dict]) -> CreatableContactZohoObject:
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

        return CreatableContactZohoObject(
            attendee_dict,
            self.zoho_api_manager,
        )

    def zoho_deal(self, contact_names: str) -> CreatableDealZohoObject:
        deal_dict = {
            "properties": {
                # "amount": "",
                # "closedate": "",
                "dealname": f"Deal for {contact_names}",
                "pipeline": "default",
                "dealstage": self.configuration.initial_deal_stage_id,
            }
        }

        return CreatableDealZohoObject(
            deal_dict,
            self.zoho_api_manager,
        )

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

        return CreatableMeetingZohoObject(
            meeting_dict,
            self.zoho_api_manager,
        )

    def zoho_note(self, transcript: str) -> CreatableNoteZohoObject:
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

        return CreatableNoteZohoObject(
            note_dict,
            self.zoho_api_manager
        )

    def extract(self, context: t.Optional[dict] = None) -> dict:
        meeting_id = context["meeting_id"]
        transcript, emails, names, organizer_email = self.fireflies_api_manager.transcript(meeting_id)
        fireflies_attendees = [
            {"name": name, "email": email}
            for name, email in zip(names, emails)
        ]

        # Only attendees that are not from our client's email domain should be
        # contacts in HubSpot.
        contactable_attendees = []
        for attendee in fireflies_attendees:
            if not attendee["email"].endswith(self.configuration.email_domain):
                contactable_attendees.append(attendee)

        return {
            "fireflies_transcript": transcript,
            "contactable_attendees": contactable_attendees,
            "organizer_email": organizer_email,
        }

    def transform(self, data: dict, context: t.Optional[dict] = None):

        fireflies_transcript = data["fireflies_transcript"]
        contactable_attendees = data["contactable_attendees"]
        organizer_email = data["organizer_email"]
        contacts = []
        deals = []

        for contactable_attendee in contactable_attendees:
            try:
                resp = self.zoho_api_manager.contact_by_name_or_email(**contactable_attendee)
                extant_contact = ExtantContactZohoObject(resp, self.zoho_api_manager)
                contacts.append(extant_contact)
            except APIError:
                contacts.append(self.zoho_contact(contactable_attendee))
        for contact in contacts:
            if isinstance(contact, ExtantContactZohoObject):
                try:
                    contact_id = contact.zoho_object_dict["id"]
                    resp = self.zoho_api_manager.deal_by_contact_id(contact_id)
                    deal_id = resp["id"]
                    resp = self.zoho_api_manager.deal_by_deal_id(deal_id, properties=["zoho_owner_id"])
                    deals.append (ExtantDealZohoObject(resp, self.zoho_api_manager))
                except APIError:
                    pass

        formatted_names = self.formatted_names(contacts)

        if len(deals) > 1: # TODO: deduplicate the same deal found from different contacts
            warning_msg = f"Too many deals found for {formatted_names}."
            current_app.logger.warning(warning_msg)
        deal = deals[0] if len(deals) > 0 else self.zoho_deal(formatted_names)

        if isinstance(deal, CreatableDealZohoObject):
            user = self.zoho_api_manager.user_by_email(organizer_email)
            deal.add_owner_from_user(ExtantUserZohoObject(user, self.zoho_api_manager))

        meeting = self.zoho_meeting(fireflies_transcript, formatted_names)
        note = self.zoho_note(fireflies_transcript)

        return {
            "contacts": contacts,
            "deal": deal,
            "meeting": meeting,
            "note": note,
        }

    def load(self, data: dict, context: t.Optional[dict] = None):
        contacts: list[ExtantContactZohoObject | CreatableContactZohoObject] = data["contacts"]
        deal: ExtantDealZohoObject | CreatableDealZohoObject = data["deal"]
        meeting: CreatableMeetingZohoObject = data["meeting"]
        note: CreatableNoteZohoObject = data["note"]

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
