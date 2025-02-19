import datetime
import itertools
import os
import typing as t
from typing import Optional
import uuid
from flask import current_app
from hubspot.files import ApiException

from ...api.fireflies.models import FirefliesCredentials

from ...api.hubspot.models import HubSpotCredentials

from ...api.fireflies.services import FirefliesAPIManager
from ...api.hubspot.services import (
    HubSpotAPIManager,
    ExtantContactHubSpotObject,
    ExtantDealHubSpotObject,
    ExtantUserHubSpotObject,
    CreatableContactHubSpotObject,
    CreatableDealHubSpotObject,
    CreatableMeetingHubSpotObject,
    CreatableNoteHubSpotObject,
)
from standard_pipelines.data_flow.exceptions import APIError

from sqlalchemy import UUID
from ..services import BaseDataFlow
from ...api.openai.services import OpenAIAPIManager
from ...api.openai.models import OpenAICredentials
from ..exceptions import InvalidWebhookError
from .models import FF2HSOnTranscriptConfiguration

class FF2HSOnTranscript(BaseDataFlow[FF2HSOnTranscriptConfiguration]):

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

    def meeting_summary(self, transcript: str) -> str:
        prompt = self.configuration.prompt.format(transcript=transcript)
        return self.openai_api_manager.chat(prompt, model=self.OPENAI_SUMMARY_MODEL).choices[0].message.content

    def formatted_names(self, contacts: t.Iterable[CreatableContactHubSpotObject | ExtantContactHubSpotObject]) -> str:
        names = [f"{contact.hubspot_object_dict['properties']['firstname']} {contact.hubspot_object_dict['properties']['lastname']}" for contact in contacts]
        if len(names) == 0:
            return "Unnamed Contact"
        if len(names) <= 3:
            return ", ".join(name for name in names)
        else:
            return f"{names[0]} et al."

    def hubspot_contact(self, attendee_dict: dict[str, str]) -> CreatableContactHubSpotObject:
        """Docs: https://developers.hubspot.com/docs/guides/api/crm/objects/contacts"""

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

        return CreatableContactHubSpotObject(
            attendee_dict,
            self.hubspot_api_manager,
        )

    def hubspot_deal(self, contact_names: str) -> CreatableDealHubSpotObject:
        deal_dict = {
            "properties": {
                # "amount": "",
                # "closedate": "",
                "dealname": f"Deal for {contact_names}",
                "pipeline": "default",
                "dealstage": self.configuration.initial_deal_stage_id,
            }
        }

        return CreatableDealHubSpotObject(
            deal_dict,
            self.hubspot_api_manager,
        )

    def hubspot_meeting(self, transcript: str, contact_names: str) -> dict:
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

        return CreatableMeetingHubSpotObject(
            meeting_dict,
            self.hubspot_api_manager,
        )

    def hubspot_note(self, transcript: str) -> CreatableNoteHubSpotObject:
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

        return CreatableNoteHubSpotObject(
            note_dict,
            self.hubspot_api_manager
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
                resp = self.hubspot_api_manager.contact_by_name_or_email(**contactable_attendee)
                extant_contact = ExtantContactHubSpotObject(resp, self.hubspot_api_manager)
                contacts.append(extant_contact)
            except APIError:
                contacts.append(self.hubspot_contact(contactable_attendee))
        for contact in contacts:
            if isinstance(contact, ExtantContactHubSpotObject):
                try:
                    contact_id = contact.hubspot_object_dict["id"]
                    resp = self.hubspot_api_manager.deal_by_contact_id(contact_id)
                    deal_id = resp["id"]
                    resp = self.hubspot_api_manager.deal_by_deal_id(deal_id, properties=["hubspot_owner_id"])
                    deals.append (ExtantDealHubSpotObject(resp, self.hubspot_api_manager))
                except APIError:
                    pass

        formatted_names = self.formatted_names(contacts)

        if len(deals) > 1: # TODO: deduplicate the same deal found from different contacts
            warning_msg = f"Too many deals found for {formatted_names}."
            current_app.logger.warning(warning_msg)
        deal = deals[0] if len(deals) > 0 else self.hubspot_deal(formatted_names)

        if isinstance(deal, CreatableDealHubSpotObject):
            user = self.hubspot_api_manager.user_by_email(organizer_email)
            deal.add_owner_from_user(ExtantUserHubSpotObject(user, self.hubspot_api_manager))

        meeting = self.hubspot_meeting(fireflies_transcript, formatted_names)
        note = self.hubspot_note(fireflies_transcript)

        return {
            "contacts": contacts,
            "deal": deal,
            "meeting": meeting,
            "note": note,
        }

    def load(self, data: dict, context: t.Optional[dict] = None):
        contacts: list[ExtantContactHubSpotObject | CreatableContactHubSpotObject] = data["contacts"]
        deal: ExtantDealHubSpotObject | CreatableDealHubSpotObject = data["deal"]
        meeting: CreatableMeetingHubSpotObject = data["meeting"]
        note: CreatableNoteHubSpotObject = data["note"]

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
