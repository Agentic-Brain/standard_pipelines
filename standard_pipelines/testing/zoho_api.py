from . import testing
from standard_pipelines.api.zoho.services import ZohoAPIManager
from standard_pipelines.api.zoho.models import ZohoCredentials
from flask import request, jsonify
from standard_pipelines.extensions import db
from flask import current_app

@testing.route("/zoho/contact/", methods=["GET"])
def get_contact_by_field():
    try:
        client_id = request.args.get('client_id')
        if not client_id:
            return jsonify({'error': 'Missing required parameter: client_id'}), 400

        # Get all query parameters except client_id
        search_params = {}
        valid_fields = {'phone', 'email', 'first_name', 'last_name'}
        for field in valid_fields:
            if value := request.args.get(field):
                search_params[field] = value

        if not search_params:
            return jsonify({'error': 'At least one search parameter is required (phone, email, first_name, last_name)'}), 400

        # Get match_all parameter (default to False)
        match_all = request.args.get('match_all', '').lower() == 'true'

        credentials = db.session.query(ZohoCredentials).filter_by(
            client_id=client_id
        ).first()
        
        if not credentials:
            return jsonify({'error': 'No Zoho credentials found for this client'}), 404

        zoho_manager = ZohoAPIManager(credentials)
        result = zoho_manager.get_contact_by_field(search_params, match_all=match_all)
        
        if result:
            return jsonify(result), 200
        else:
            return jsonify({'error': 'No contact found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@testing.route("/zoho/contact/<contact_id>", methods=["GET"])
def get_contact_by_id(contact_id):
    try:
        client_id = request.args.get('client')
        if not client_id:
            return jsonify({'error': 'Missing required parameter: client'}), 400

        credentials = db.session.query(ZohoCredentials).filter_by(
            client_id=client_id
        ).first()
        
        if not credentials:
            return jsonify({'error': 'No Zoho credentials found for this client'}), 404

        zoho_manager = ZohoAPIManager(credentials)
        result = zoho_manager.get_contact_by_contact_id(contact_id)
        
        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500





@testing.route("/zoho/contacts", methods=["GET"])
def get_all_contacts():
    try:
        client_id = request.args.get('client')
        if not client_id:
            return jsonify({'error': 'Missing required parameter: client'}), 400

        credentials = db.session.query(ZohoCredentials).filter_by(
            client_id=client_id
        ).first()
        
        if not credentials:
            return jsonify({'error': 'No Zoho credentials found for this client'}), 404

        zoho_manager = ZohoAPIManager(credentials)
        result = zoho_manager.get_all_contacts()
        
        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@testing.route("/zoho/users", methods=["GET"])
def get_all_users():
    try:
        client_id = request.args.get('client')
        if not client_id:
            return jsonify({'error': 'Missing required parameter: client'}), 400

        credentials = db.session.query(ZohoCredentials).filter_by(
            client_id=client_id
        ).first()
        
        if not credentials:
            return jsonify({'error': 'No Zoho credentials found for this client'}), 404

        zoho_manager = ZohoAPIManager(credentials)
        result = zoho_manager.get_all_users()
        
        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@testing.route("/zoho/record", methods=["POST"])
def create_record():
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['module_name', 'record_data', 'client_id']):
            return jsonify({
                'error': 'Missing required fields: module_name, record_data, client_id'
            }), 400

        module_name = data['module_name']
        record_data = data['record_data']
        client_id = data['client_id']
        parent_record = data.get('parent_record')  # Optional parent record

        credentials = db.session.query(ZohoCredentials).filter_by(
            client_id=client_id
        ).first()
        
        if not credentials:
            return jsonify({'error': 'No Zoho credentials found for this client'}), 404

        zoho_manager = ZohoAPIManager(credentials)
        result = zoho_manager.create_record(module_name, record_data, parent_record=parent_record)
        
        return jsonify(result), 201

    except Exception as e:
        error_message = str(e)
        current_app.logger.exception(f"Error creating record: {error_message}")
        return jsonify({'error': error_message}), 500

@testing.route("/zoho/note", methods=["POST"])
def create_note():
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['note_data', 'parent_record_id', 'parent_module', 'client_id']):
            return jsonify({
                'error': 'Missing required fields: note_data, parent_record_id, parent_module, client_id'
            }), 400

        note_data = data['note_data']
        parent_record_id = data['parent_record_id']
        parent_module = data['parent_module']
        client_id = data['client_id']

        credentials = db.session.query(ZohoCredentials).filter_by(
            client_id=client_id
        ).first()
        
        if not credentials:
            return jsonify({'error': 'No Zoho credentials found for this client'}), 404

        zoho_manager = ZohoAPIManager(credentials)
        result = zoho_manager.create_note(note_data, parent_record_id, parent_module)
        
        return jsonify(result), 201

    except Exception as e:
        error_message = str(e)
        current_app.logger.exception(f"Error creating note: {error_message}")
        return jsonify({'error': error_message}), 500
