import datetime
import typing as t
from flask import current_app
from functools import cached_property
from ..services import BaseDataFlowService
from ..utils import HubSpotAPIManager, FirefliesAPIManager
from ..exceptions import InvalidWebhookError
from .models import HubSpotDraftEmailOnFirefliesTranscriptConfiguration

class HubSpotDraftEmailOnFirefliesTranscript(BaseDataFlowService):

    MEETING_TO_CONTACT_ASSOCIATION_ID = 200
    MEETING_TO_DEAL_ASSOCIATION_ID = 212
    NOTE_TO_DEAL_ASSOCIATION_ID = 214

    @cached_property
    def hubspot_api_manager(self) -> HubSpotAPIManager:
        data_flow_config = HubSpotDraftEmailOnFirefliesTranscriptConfiguration.query.filter_by(
            client_id=self.client_id,
        ).first()
        hubspot_config = {
            "client_id": self.bitwarden_api_manager.get_secret(data_flow_config.hubspot_client_id_bitwarden_id),
            "client_secret": self.bitwarden_api_manager.get_secret(data_flow_config.hubspot_client_secret_bitwarden_id),
            "refresh_token": self.bitwarden_api_manager.get_secret(data_flow_config.hubspot_refresh_token_bitwarden_id)
        }
        return HubSpotAPIManager(hubspot_config)

    @cached_property
    def fireflies_api_manager(self) -> FirefliesAPIManager:
        data_flow_config = HubSpotDraftEmailOnFirefliesTranscriptConfiguration.query.filter_by(
            client_id=self.client_id,
        ).first()
        fireflies_config = {
            "api_key": self.bitwarden_api_manager.get_secret(data_flow_config.fireflies_api_key_bitwarden_id)
        }
        return FirefliesAPIManager(fireflies_config)

    def context_from_webhook_data(self, webhook_data: t.Any) -> t.Optional[dict]:
        if not isinstance(webhook_data, dict):
            raise InvalidWebhookError('Invalid webhook data')
        if webhook_data.get("eventType") != "Transcription completed":
            return None
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

    def email_body(self, transcript: str) -> str:
        """
        TODO: generate email body using chatgpt
        """
        return transcript[:1000]

    def meeting_summary(self, transcript: str) -> str:
        """
        TODO: generate meeting summary using chatgpt
        """
        return transcript[:100]

    def hubspot_association(to_id: str, type_category: str, type_id: str) -> dict:
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

    def hubspot_meeting(self, transcript: str, contacts: list[dict], deal: dict) -> dict:
        now = datetime.datetime.now()
        contact_names = [contact["properties"]["firstname"] + " " + contact["properties"]["lastname"] for contact in contacts]
        contact_names_str = ", ".join(contact_names)
        
        return {
            "properties": {
                "hs_timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "hubspot_owner_id": deal["properties"]["hubspot_owner_id"],
                "hs_meeting_title": "Meeting with " + contact_names_str,
                "hs_meeting_body": "Meeting with " + contact_names_str,
                # "hs_internal_meeting_notes": "",
                "hs_meeting_location": "Remote",
                "hs_meeting_start_time": now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                # "hs_meeting_end_time": "",
                "hs_meeting_outcome": "COMPLETED"
            },
            "associations": [
                *[self.hubspot_association(contact["id"], "HUBSPOT_DEFINED", self.MEETING_TO_CONTACT_ASSOCIATION_ID) for contact in contacts],
                self.hubspot_association(deal["id"], "HUBSPOT_DEFINED", self.MEETING_TO_DEAL_ASSOCIATION_ID)
            ]
        }

    def hubspot_note(self, transcript: str, contacts: list[dict], deal: dict) -> dict:
        now = datetime.datetime.now()

        return {
            "properties": {
                "hs_timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "hs_note_body": self.meeting_summary(transcript),
                "hubspot_owner_id": deal["properties"]["hubspot_owner_id"],
                # "hs_attachment_ids": ""
            },
            "associations": [
                self.hubspot_association(deal["id"], "HUBSPOT_DEFINED", self.NOTE_TO_DEAL_ASSOCIATION_ID)
            ]
        }

    def transform(self, data: dict, context: t.Optional[dict] = None):
        if len(data["deals"]) > 1:
            raise ValueError("More than one deal found")
        deal = data["deals"][0]
        meeting = self.hubspot_meeting(data["transcript"], data["contacts"], deal)
        note = self.hubspot_note(data["transcript"], data["contacts"], deal)
        # email = self.gmail_or_outlook_email(data["transcript"], data["contacts"], deal) # TODO: implement
        return {
            "meeting": meeting,
            "note": note,
            # "email": email # TODO: implement
        }

    def load(self, data: dict, context: t.Optional[dict] = None):
        self.hubspot_api_manager.create_meeting(data["meeting"])
        self.hubspot_api_manager.create_note(data["note"])
        # self.email_api_manager.send_email(data["email"]) # TODO: implement
