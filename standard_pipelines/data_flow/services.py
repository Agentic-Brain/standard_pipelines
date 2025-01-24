from flask import current_app
from .models import ClientDataFlowJoin
from .utils import BaseDataFlow,DataFlowRegistryMeta
from .ff2hs_on_transcript.services import FF2HSOnTranscript

def determine_data_flow_service(webhook_id: str) -> BaseDataFlow:
    client_data_flow = ClientDataFlowJoin.query.filter_by(webhook_id=str(webhook_id)).first()
    client_id = client_data_flow.client_id
    data_flow_id = client_data_flow.data_flow_id
    data_flow_class = DataFlowRegistryMeta.data_flow_class(data_flow_id)
    return data_flow_class(client_id=client_id)