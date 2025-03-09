from . import testing
from standard_pipelines.api.zoho.services import ZohoAPIManager
from standard_pipelines.api.zoho.models import ZohoCredentials
from flask import request, jsonify
from standard_pipelines.extensions import db
from flask import current_app



@testing.route("/zoho/contact/<contact_id>", methods=["GET"])
def get_contact_by_id(contact_id):
    try:
        client_id = request.args.get('client_id')
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
        client_id = request.args.get('client_id')
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
        client_id = request.args.get('client_id')
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

        credentials = db.session.query(ZohoCredentials).filter_by(
            client_id=client_id
        ).first()
        
        if not credentials:
            return jsonify({'error': 'No Zoho credentials found for this client'}), 404

        zoho_manager = ZohoAPIManager(credentials)
        result = zoho_manager.create_record(module_name, record_data)
        
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

@testing.route("/zoho/record/<module_name>/<record_id>", methods=["GET"])
def get_record_by_id(module_name, record_id):
    try:
        client_id = request.args.get('client_id')
        if not client_id:
            return jsonify({'error': 'Missing required parameter: client_id'}), 400

        credentials = db.session.query(ZohoCredentials).filter_by(
            client_id=client_id
        ).first()
        
        if not credentials:
            return jsonify({'error': 'No Zoho credentials found for this client'}), 404

        zoho_manager = ZohoAPIManager(credentials)
        result = zoho_manager.get_record_by_id(module_name, record_id)
        
        return jsonify(result), 200

    except Exception as e:
        error_message = str(e)
        current_app.logger.exception(f"Error retrieving record: {error_message}")
        return jsonify({'error': error_message}), 500

@testing.route("/zoho/record/search/<module_name>", methods=["GET"])
def search_record_by_field(module_name):
    try:
        client_id = request.args.get('client_id')
        if not client_id:
            return jsonify({'error': 'Missing required parameter: client_id'}), 400

        # Get match_all parameter (default to False)
        match_all = request.args.get('match_all', '').lower() == 'true'
        
        # Extract all other query parameters as field criteria
        field_criteria = {}
        for key, value in request.args.items():
            # Skip client_id and match_all parameters
            if key not in ['client_id', 'match_all']:
                field_criteria[key] = value
        
        if not field_criteria:
            return jsonify({'error': 'At least one field criterion must be provided as a query parameter'}), 400

        credentials = db.session.query(ZohoCredentials).filter_by(
            client_id=client_id
        ).first()
        
        if not credentials:
            return jsonify({'error': 'No Zoho credentials found for this client'}), 404

        zoho_manager = ZohoAPIManager(credentials)
        result = zoho_manager.get_record_by_field(module_name, field_criteria, match_all=match_all)
        
        if result:
            return jsonify(result), 200
        else:
            return jsonify({'error': f'No {module_name} found with the provided criteria'}), 404

    except Exception as e:
        error_message = str(e)
        current_app.logger.exception(f"Error searching for record: {error_message}")
        return jsonify({'error': error_message}), 500

@testing.route("/zoho/record/lookup/<module_name>/<lookup_field>/<lookup_id>", methods=["GET"])
def search_by_lookup_field(module_name, lookup_field, lookup_id):
    try:
        client_id = request.args.get('client_id')
        if not client_id:
            return jsonify({'error': 'Missing required parameter: client_id'}), 400

        credentials = db.session.query(ZohoCredentials).filter_by(
            client_id=client_id
        ).first()
        
        if not credentials:
            return jsonify({'error': 'No Zoho credentials found for this client'}), 404

        zoho_manager = ZohoAPIManager(credentials)
        results = zoho_manager.search_by_lookup_field(module_name, lookup_field, lookup_id)
        
        if results:
            return jsonify(results), 200
        else:
            return jsonify({'error': f'No {module_name} records found with {lookup_field}.id = {lookup_id}'}), 404

    except Exception as e:
        error_message = str(e)
        current_app.logger.exception(f"Error searching by lookup field: {error_message}")
        return jsonify({'error': error_message}), 500
