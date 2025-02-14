from . import testing
from standard_pipelines.api.google.gmail_services import GmailAPIManager
from flask_login import current_user
from flask import request, jsonify
from standard_pipelines.api.google.models import GoogleCredentials
from standard_pipelines.extensions import db

@testing.route("/gmail/send-email", methods=["POST"])
def gmail_test():
    try:
        # Get request data
        data = request.get_json()
        if not data or not all(k in data for k in ['to', 'subject', 'body', 'client']):
            return jsonify({'error': 'Missing required fields: to, subject, body'}), 400

        # Get Google credentials for current user's client
        credentials = db.session.query(GoogleCredentials).filter_by(
            client_id=data['client']
        ).first()
        
        if not credentials:
            return jsonify({'error': 'No Google credentials found for this client'}), 404

        # Initialize Gmail API manager
        gmail_manager = GmailAPIManager({
            'refresh_token': credentials.refresh_token
        })

        # Send email
        result = gmail_manager.send_email(
            to_address=data['to'],
            subject=data['subject'],
            body=data['body']
        )

        if 'error' in result:
            return jsonify(result), 400
            
        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
