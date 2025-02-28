from flask import current_app
from standard_pipelines.api import api
from standard_pipelines.api.sharpspring.models import SharpSpringCredentials
from standard_pipelines.data_flow.models import Client
from standard_pipelines.extensions import db
from flask import jsonify, request
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from uuid import UUID


@api.route('/sharpspring/credentials/<client_id>', methods=['POST'])
def create_sharpspring_credentials(client_id: str):
    """Test endpoint to set SharpSpring credentials for a client."""
    try:
        current_app.logger.info(f"Saving client credentials for client: {client_id}")
        client_uuid = UUID(client_id)
        client = Client.query.get_or_404(client_uuid)

        data = request.get_json()
        
        required_fields = {'account_id': str, 'secret_key': str}
        for field, field_type in required_fields.items():
            if field not in data:
                current_app.logger.error(f"Missing required field: {field}")
                return jsonify({'error': f"Missing required field: {field}"}), 400
            if not isinstance(data[field], field_type):
                current_app.logger.error(f"Invalid type for {field}. Expected {field_type.__name__}")
                return jsonify({'error': f"Invalid type for {field}. Expected {field_type.__name__}"}), 400
            if not data[field].strip():
                current_app.logger.error(f"Empty value provided for {field}")
                return jsonify({'error': f"Empty value provided for {field}"}), 400

        credentials = SharpSpringCredentials( 
            client_id=client_uuid, 
            account_id=data['account_id'],
            secret_key=data['secret_key']
        ) 
        credentials.client = client
        credentials.save()

        current_app.logger.info(f"Credentials saved successfully for client: {client.name}")
        return jsonify({'message': 'Credentials saved successfully', 'client': client.name}), 201

    except IntegrityError:
        db.session.rollback()
        current_app.logger.error(f"Credentials already exist for client: {client_id}")
        return jsonify({'error': 'Credentials already exist for this client'}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    except ValueError:
        current_app.logger.error(f"Invalid client ID format: {client_id}")
        return jsonify({'error': 'Invalid client ID format'}), 400
    except Exception as e:
        current_app.logger.exception(f"Unknown error with managing SharpSpring credentials: {e}")
        return jsonify({'error': f"Unknown error with managing SharpSpring credentials: {e}"}), 500
