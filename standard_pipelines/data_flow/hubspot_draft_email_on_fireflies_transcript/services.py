import typing as t
from flask import current_app
from functools import cached_property
from ..services import BaseDataFlowService
from ..utils import HubSpotAPIManager, FirefliesAPIManager
from ..exceptions import InvalidWebhookError
from .models import HubSpotDraftEmailOnFirefliesTranscriptConfiguration

class HubSpotDraftEmailOnFirefliesTranscript(BaseDataFlowService):

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
        transcript = self.fireflies_api_manager.get_transcript(meeting_id)
        input_data = {
            "transcript": transcript
        }
        return input_data

    def transform(self, data: t.Any = None, context: t.Optional[dict] = None):
        pass

    def load(self, context: t.Optional[dict] = None):
        pass

    # TODO: lookup based on the specific client
    # TODO: allow multiple recipients per URI
    # TODO: allow multiple URIs per client?
    @property
    def _apprise_uri(self): 

        if not self.verify_config('MAILGUN_API_KEY'):
            return None
        if not self.verify_config('MAILGUN_SEND_DOMAIN'):
            return None
        if not self.verify_config('MAILGUN_SEND_USER'):
            return None
        if not self.verify_config('MAILGUN_RECIPIENT'):
            return None

        user = current_app.config['MAILGUN_SEND_USER']
        domain = current_app.config['MAILGUN_SEND_DOMAIN']
        apikey = current_app.config['MAILGUN_API_KEY']
        emails = [current_app.config['MAILGUN_RECIPIENT']]
        return f'mailgun://{user}@{domain}/{apikey}/{"/".join(emails)}'
