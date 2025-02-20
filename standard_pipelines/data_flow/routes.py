from flask import current_app, jsonify, request
import requests
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

@data_flow.route('/webhook-split', methods=['POST'])
def webhook_split():
    current_app.logger.info('Received webhook-split request')
    if request.method == 'POST':
        try:
            # Get webhook IDs as a comma-separated string and split into list
            webhook_ids_str = request.args.get('webhook_ids', '')
            webhook_ids = [id.strip() for id in webhook_ids_str.split(',') if id.strip()]
            
            if not webhook_ids:
                return jsonify({'error': 'No webhook IDs provided'}), 400

            # Validate all webhook IDs are valid UUIDs
            try:
                validated_ids = [str(UUID(webhook_id)) for webhook_id in webhook_ids]
            except ValueError:
                return jsonify({'error': 'Invalid UUID format in webhook IDs'}), 400

            # Get the original request data
            webhook_data = request.get_json(silent=True)
            if webhook_data is None:
                return jsonify({'error': 'Invalid JSON in request body'}), 400

            # Forward the request to each webhook endpoint
            results = []
            for webhook_id in validated_ids:
                response = requests.post(
                    f'http://localhost:5000/webhook/{webhook_id}', 
                    json=webhook_data  # requests will handle JSON serialization
                )
                results.append({
                    'webhook_id': webhook_id,
                    'status': 'success' if response.status_code == 200 else 'error'
                })

            return jsonify({
                'status': 'success',
                'results': results
            }), 200

        except Exception as e:
            current_app.logger.error(f'Error processing webhook-split: {str(e)}')
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error'}), 500

    return jsonify({'error': 'Method not allowed'}), 405