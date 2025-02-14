from ..services import BaseDataFlow
from .models import GmailIntervalFollowupConfiguration
from standard_pipelines.api.google.models import GoogleCredentials
from standard_pipelines.api.hubspot.models import HubSpotCredentials
from standard_pipelines.api.openai.models import OpenAICredentials
from standard_pipelines.api.hubspot.services import HubSpotAPIManager
from standard_pipelines.api.google.gmail_services import GmailAPIManager
from standard_pipelines.api.openai.services import OpenAIAPIManager
from functools import cached_property
from typing import Optional

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
    def google_api_manager(self) -> GmailAPIManager:
        credentials = GoogleCredentials.query.filter_by(client_id=self.client_id).first()
        google_config = {
            "api_key": credentials.google_api_key
        }
        return GoogleAPIManager(google_config)