from flask import current_app, jsonify, request

from . import data_flow
from .services import determine_data_flow_service

@data_flow.route('/webhook/<string:webhook_id>', methods=['POST'])
def webhook(webhook_id: str):
    current_app.logger.info(f'Received webhook for {webhook_id}')
    if request.method == 'POST':
        try:
            webhook_data = request.get_json(silent=True)
            if webhook_data is None:
                webhook_data = request.get_data(as_text=True)

            data_flow_service = determine_data_flow_service(webhook_id)
            data_flow_service.webhook_run(webhook_data)

            return jsonify({'status': 'success', 'message': 'Webhook received'}), 200
        except Exception as e:
            current_app.logger.error(f'Error processing webhook: {str(e)}')
            return jsonify({'error': 'Internal server error'}), 500
    
    return jsonify({'error': 'Method not allowed'}), 405