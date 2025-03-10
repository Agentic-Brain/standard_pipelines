from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import Session
from .models import OpenAICredentials
from standard_pipelines.extensions import db
from standard_pipelines.main.decorators import require_api_key
from standard_pipelines.data_flow.models import Client
from .. import api
from uuid import UUID

@api.route('/credentials/openai/<client_id>', methods=['POST'])
@require_api_key
def create_openai_credentials(client_id: UUID):
    try:
        data = request.get_json()
        
        # Validate required fields using set operations
        required_fields = {'openai_api_key'}
        missing_fields = required_fields - data.keys()
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        # Create new credentials
        credentials = OpenAICredentials(
            client_id=client_id,
            openai_api_key=data['openai_api_key']
        )
        
        client = Client.query.get_or_404(client_id)
        credentials.client = client
        
        db.session.add(credentials)
        db.session.commit()
        
        return jsonify({
            'message': 'OpenAI credentials created successfully',
            'id': str(credentials.id)
        }), 201
        
    except Exception as e:
        current_app.logger.error(f'Error creating OpenAI credentials: {str(e)}')
        db.session.rollback()
        return jsonify({'error': str(e)}), 500