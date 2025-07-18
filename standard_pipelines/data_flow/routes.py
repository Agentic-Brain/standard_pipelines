import json
from flask import current_app, jsonify, request, url_for, redirect
import requests
from standard_pipelines.api.hubspot.models import HubSpotCredentials
from standard_pipelines.api.fireflies.models import FirefliesCredentials
from standard_pipelines.extensions import db
from uuid import UUID
from .models import Client, ClientDataFlowJoin
from . import data_flow
from .services import determine_data_flow_service
import sentry_sdk
import jwt
from standard_pipelines.api.dialpad.models import DialpadCredentials
from .services import extract_webhook_data, process_webhook
import time

# TODO: write function to extract data from request here, gonna need to check for jwt, move this and process_webhook to the services file



@data_flow.route('/webhook/<string:client_data_flow_join_id>', methods=['POST'])
def webhook(client_data_flow_join_id: str):
    current_app.logger.info(f'Received webhook for {client_data_flow_join_id}')
    if request.method == 'POST':
        try:
            webhook_data = extract_webhook_data(request, client_data_flow_join_id)
            if webhook_data is None:
                return jsonify({'error': 'Invalid request data'}), 400

            current_app.logger.debug(f'Webhook data: {json.dumps(webhook_data, indent=4)}')
            process_webhook(client_data_flow_join_id, webhook_data)
            return {'status': 'success', 'message': 'Webhook received'}
        except Exception as e:
            current_app.logger.error(f'Error processing webhook: {str(e)}')
            sentry_sdk.capture_exception(e)
            db.session.rollback()
            return jsonify({'error': 'Internal server error'}), 500
    
    return jsonify({'error': 'Method not allowed'}), 405

@data_flow.route('/webhook-split', methods=['POST'])
def webhook_split():
    current_app.logger.info('Received webhook-split request')
    webhook_ids_str = request.args.get('webhook_ids', '')
    webhook_ids = [id.strip() for id in webhook_ids_str.split(',') if id.strip()]
    
    if not webhook_ids:
        return jsonify({'error': 'No webhook IDs provided'}), 400

    try:
        validated_ids = [str(UUID(webhook_id)) for webhook_id in webhook_ids]
    except ValueError:
        return jsonify({'error': 'Invalid UUID format in webhook IDs'}), 400

    webhook_data = request.get_json(silent=True)
    if webhook_data is None:
        return jsonify({'error': 'Invalid JSON in request body'}), 400

    results = []
    for webhook_id in validated_ids:
        try:
            # Directly call the helper function
            process_webhook(webhook_id, webhook_data)
            results.append({'webhook_id': webhook_id, 'status': 'success'})
            current_app.logger.info(f'Wait 5 seconds before executing next webhook')
            time.sleep(5)
        except Exception as e:
            current_app.logger.error(f'Error processing webhook for {webhook_id}: {str(e)}')
            results.append({'webhook_id': webhook_id, 'status': 'error'})
            sentry_sdk.capture_exception(e)

    return jsonify({'status': 'success', 'results': results}), 200