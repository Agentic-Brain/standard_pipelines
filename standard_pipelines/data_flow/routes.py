from flask import current_app, jsonify, request
from standard_pipelines.api.hubspot.models import HubSpotCredentials
from standard_pipelines.api.fireflies.models import FirefliesCredentials
from standard_pipelines.extensions import db
from uuid import UUID
from .models import Client
from . import data_flow
from .services import determine_data_flow_service
import sentry_sdk

@data_flow.route('/webhook/<string:client_data_flow_join_id>', methods=['POST'])
def webhook(client_data_flow_join_id: str):
    current_app.logger.info(f'Received webhook for {client_data_flow_join_id}')
    if request.method == 'POST':
        try:
            webhook_data = request.get_json(silent=True)
            if webhook_data is None:
                webhook_data = request.get_data(as_text=True)

            data_flow_service = determine_data_flow_service(client_data_flow_join_id)
            data_flow_service.webhook_run(webhook_data)

            return jsonify({'status': 'success', 'message': 'Webhook received'}), 200
        except Exception as e:
            current_app.logger.error(f'Error processing webhook: {str(e)}')
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error'}), 500
    
    return jsonify({'error': 'Method not allowed'}), 405

