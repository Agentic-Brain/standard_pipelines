from flask import current_app
from .models import ClientDataFlowJoin, DataFlow
from .utils import BaseDataFlow,DataFlowRegistryMeta
from standard_pipelines.api.dialpad.models import DialpadCredentials
import jwt
import sentry_sdk
from standard_pipelines.extensions import db
def determine_data_flow_service(client_data_flow_join_id: str) -> BaseDataFlow:
    client_data_flow = ClientDataFlowJoin.query.filter_by(id=str(client_data_flow_join_id)).first()
    if not client_data_flow:
        current_app.logger.error(f'No client data flow join found for ID: {client_data_flow_join_id}')
        raise ValueError(f'No client data flow join found for ID: {client_data_flow_join_id}')
    client_id = client_data_flow.client_id
    data_flow_id = client_data_flow.data_flow_id
    data_flow = DataFlow.query.filter_by(id=data_flow_id).first()
    if not data_flow:
        current_app.logger.error(f'No data flow found for ID: {data_flow_id}')
        raise ValueError(f'No data flow found for ID: {data_flow_id}')
    data_flow_class = DataFlowRegistryMeta.data_flow_class(data_flow.name)
    return data_flow_class(client_id=client_id)

def process_webhook(client_data_flow_join_id: str, webhook_data):
    try:
        data_flow_service = determine_data_flow_service(client_data_flow_join_id)
        data_flow_service.webhook_run(webhook_data)
    except Exception as e:
        current_app.logger.error(f'Error processing webhook: {str(e)}')
        sentry_sdk.capture_exception(e)
        db.session.rollback()

def extract_webhook_data(request, client_data_flow_join_id=None):
    if request.mimetype == 'application/json':
        return request.get_json(silent=True)
    elif request.mimetype == 'application/x-www-form-urlencoded':
        return request.form.to_dict()
    elif request.mimetype == 'application/jwt':
        try:
            # Get the client from the join ID
            join = ClientDataFlowJoin.query.get(client_data_flow_join_id)
            if not join:
                current_app.logger.error(f'No client data flow join found for ID: {client_data_flow_join_id}')
                return None

            # Get the Dialpad credentials for this client
            dialpad_creds = DialpadCredentials.query.filter_by(client_id=join.client_id).first()
            if not dialpad_creds:
                current_app.logger.error(f'No Dialpad credentials found for client ID: {join.client_id}')
                return None

            data = request.get_data(as_text=True)
            decoded_data = jwt.decode(data, dialpad_creds.dialpad_jwt_secret, algorithms=['HS256'])
            return decoded_data
        except jwt.InvalidTokenError as e:
            current_app.logger.error(f'JWT decode error: {str(e)}')
            return None
        except Exception as e:
            current_app.logger.error(f'Error processing JWT: {str(e)}')
            return None
    else:
        return None
