from flask import render_template, current_app, jsonify, request, redirect, url_for, flash
from .services import HubSpotNotificationEmailOnContactUpdate
from .. import data_flow
from standard_pipelines.extensions import db

# REMOVE: This will all be removed shortly, just keeping it until new base data flow is implemented
# Both commented out to prevent webhook endpoint collision

# @data_flow.route('/sync', methods=['GET', 'POST'])
# def sync():
#     data_flow_service = HubSpotNotificationEmailOnContactUpdate.new_instance_from_env()
#     current_app.logger.info(f'Received request to sync: {request}')
#     if request.method == 'POST':
#         data_flow_service.load_context()
#         flash('Context loaded successfully!', 'success')
#         return redirect(url_for('data_flow.sync'))
#     return render_template('data_flow/sync.html')

# Commented out to prevent webhook endpoint collision

# @data_flow.route('/webhook', methods=['POST'])
# def hubspot_webhook():
#     """
#     Webhook endpoint for Hubspot API callbacks.
#     Expects JSON payload from Hubspot when a call transcript is generated.
#     """
#     data_flow_service = HubSpotNotificationEmailOnContactUpdate.new_instance_from_env()
#     if request.method == 'POST':
#         try:
#             payload = request.get_json()
#             if not payload:
#                 return jsonify({'error': 'No payload received'}), 400

#             data_flow_service.run(data=payload, context=None)

#             # Return a success response
#             return jsonify({'status': 'success', 'message': 'Webhook received'}), 200
            
#         except Exception as e:
#             current_app.logger.error(f'Error processing webhook: {str(e)}')
#             return jsonify({'error': 'Internal server error'}), 500
    
#     return jsonify({'error': 'Method not allowed'}), 405