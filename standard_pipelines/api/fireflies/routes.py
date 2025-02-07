from standard_pipelines.auth import auth
from standard_pipelines.auth.models import FirefliesCredentials
from standard_pipelines.data_flow.models import Client
from standard_pipelines.extensions import db


from flask import jsonify, request
from sqlalchemy.exc import IntegrityError


from uuid import UUID


@auth.route('/api/credentials/fireflies/<client_id>', methods=['GET', 'POST'])
def manage_fireflies_credentials(client_id: str):
    """Test endpoint to manage Fireflies credentials for a client."""
    try:
        client_uuid = UUID(client_id)
        client = Client.query.get_or_404(client_uuid)

        if request.method == 'POST':
            # Get API key from request
            data = request.get_json()
            if not data or 'api_key' not in data:
                return jsonify({'error': 'api_key is required'}), 400

            try:
                # Create and save new credentials
                credentials = FirefliesCredentials( # type: ignore
                    client_id=client_uuid, # type: ignore
                    api_key=data['api_key'] # type: ignore
                ) # type: ignore
                credentials.client = client
                credentials.save()

                return jsonify({
                    'message': 'Credentials saved successfully',
                    'client': client.name
                }), 201

            except IntegrityError:
                db.session.rollback()
                return jsonify({
                    'error': 'Credentials already exist for this client'
                }), 409

        else:  # GET request
            # Retrieve existing credentials
            new_credentials = FirefliesCredentials.query.filter_by(client_id=client_uuid).first()

            if not new_credentials:
                return jsonify({
                    'error': 'No credentials found for this client'
                }), 404

            return jsonify({
                'client': client.name,
                'api_key': new_credentials.api_key
            })

    except ValueError:
        return jsonify({'error': 'Invalid client ID format'}), 400