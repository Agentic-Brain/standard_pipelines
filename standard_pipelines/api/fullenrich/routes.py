from flask import current_app
from standard_pipelines.api import api
from standard_pipelines.api.fullenrich.models import FullEnrichCredentials
from standard_pipelines.data_flow.models import Client
from standard_pipelines.extensions import db
from flask import jsonify, request
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from standard_pipelines.main.decorators import require_api_key
from uuid import UUID


@api.route('/fullenrich/credentials/<client_id>', methods=['GET', 'POST'])
def manage_fullenrich_credentials(client_id: str):
    """Test endpoint to manage FullEnrich credentials for a client."""
    try:
        client_uuid = UUID(client_id)
        client = Client.query.get_or_404(client_uuid)
        existing_credentials = FullEnrichCredentials.query.filter_by(client_id=client_uuid).first()

        # Create new credentials
        if request.method == 'POST':
            current_app.logger.info(f"Saving credentials for client: {client.name}")
            if existing_credentials:
                current_app.logger.error(f"Credentials already exist for client: {client_id}")
                return jsonify({'error': 'Credentials already exist for this client'}), 400

            data = request.get_json()
            if not data or 'api_key' not in data or not isinstance(data['api_key'], str) or not data['api_key'].strip():
                current_app.logger.error(f"Invalid request data: {data}")
                return jsonify({'error': 'Proper api_key format is required'}), 400

            credentials = FullEnrichCredentials( 
                client_id=client_uuid, 
                api_key=data['api_key'] 
            ) 
            credentials.client = client
            credentials.save()

            current_app.logger.info(f"Credentials saved successfully for client: {client.name}")
            return jsonify({'message': 'Credentials saved successfully', 'client': client.name}), 201

        # Get existing credentials
        else:  
            if not existing_credentials:
                current_app.logger.error(f"No credentials found for client: {client_id}")
                return jsonify({'error': 'No credentials found for this client'}), 404

            current_app.logger.info(f"Returning credentials for client: {client.name}")
            return jsonify({'client': client.name,'api_key': existing_credentials.api_key})

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error occured while handling credentials: {e}")
        if isinstance(e, IntegrityError):
            return jsonify({'error': 'A database conflict occurred while saving credentials'}), 500
        return jsonify({'error': f'Error storing credentials: {e}'}), 500
    except ValueError:
        current_app.logger.error(f"Invalid client ID format: {client_id}")
        return jsonify({'error': 'Invalid client ID format'}), 400
    except Exception as e:
        current_app.logger.exception(f"Unknown error with managing FullEnrich credentials: {e}")
        return jsonify({'error': f"Unknown error with managing FullEnrich credentials: {e}"}), 500

