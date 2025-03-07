from flask import current_app
from .models import ClientDataFlowJoin, DataFlow
from .utils import BaseDataFlow,DataFlowRegistryMeta

def determine_data_flow_service(client_data_flow_join_id: str) -> BaseDataFlow:
    client_data_flow = ClientDataFlowJoin.query.filter_by(id=str(client_data_flow_join_id)).first()
    client_id = client_data_flow.client_id
    data_flow_id = client_data_flow.data_flow_id
    data_flow_name = DataFlow.query.filter_by(id=data_flow_id).first().name
    data_flow_class = DataFlowRegistryMeta.data_flow_class(data_flow_name)
    return data_flow_class(client_id=client_id)

# TODO: check for jwt here
