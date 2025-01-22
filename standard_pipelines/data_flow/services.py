import contextlib
from functools import cached_property
import io
from flask import current_app
import requests
from .models import ClientDataFlowRegistryJoin, Client, DataFlowRegistry
from standard_pipelines.extensions import db
from hubspot import HubSpot
import hubspot.oauth.exceptions
from .utils import BaseDataFlowService
from .hubspot_draft_email_on_fireflies_transcript.services import HubSpotDraftEmailOnFirefliesTranscript


# TODO: replace with the production names we plan to use for these data flows
DATA_FLOW_NAMES_TO_CLASSES: dict[str, type[BaseDataFlowService]] = {
    'hubspot_draft_email_on_fireflies_transcript': HubSpotDraftEmailOnFirefliesTranscript
}

def determine_data_flow_service(webhook_id: str) -> BaseDataFlowService:
    client_data_flow = ClientDataFlowRegistryJoin.query.filter_by(webhook_id=str(webhook_id)).first()
    client_id = client_data_flow.client_id
    data_flow_id = client_data_flow.data_flow_id
    data_flow_name = DataFlowRegistry.query.filter_by(id=data_flow_id).first().name
    data_flow_class = DATA_FLOW_NAMES_TO_CLASSES[data_flow_name]
    return data_flow_class(client_id=client_id)
