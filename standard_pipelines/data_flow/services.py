from flask import current_app
from .models import ClientDataFlowRegistryJoin
from .utils import BaseDataFlowService
from .ff2hs_on_transcript.services import FF2HSOnTranscript


# TODO: replace with the production names we plan to use for these data flows
# TODO: is there a better way to abstract this functionality?
DATA_FLOW_IDS_TO_CLASSES: dict[str, type[BaseDataFlowService]] = {
    FF2HSOnTranscript.data_flow_id(): FF2HSOnTranscript
}   

def determine_data_flow_service(webhook_id: str) -> BaseDataFlowService:
    client_data_flow = ClientDataFlowRegistryJoin.query.filter_by(webhook_id=str(webhook_id)).first()
    client_id = client_data_flow.client_id
    data_flow_id = client_data_flow.data_flow_id
    data_flow_class = DATA_FLOW_IDS_TO_CLASSES[data_flow_id]
    return data_flow_class(client_id=client_id)
