from . import testing
from standard_pipelines.api.zoho.services import ZohoAPIManager
from standard_pipelines.api.zoho.models import ZohoCredentials
from flask import request, jsonify
from standard_pipelines.extensions import db

@testing.route("/zoho/contact/phone", methods=["GET"])
def get_contact_by_phone():
    try:
        phone = request.args.get('phone')
        client_id = request.args.get('client_id')
        
        if not phone or not client_id:
            return jsonify({'error': 'Missing required parameters: phone, client'}), 400

        credentials = db.session.query(ZohoCredentials).filter_by(
            client_id=client_id
        ).first()
        
        if not credentials:
            return jsonify({'error': 'No Zoho credentials found for this client'}), 404

        zoho_manager = ZohoAPIManager(credentials)
        result = zoho_manager.get_contact_by_phone(phone)
        
        return jsonify(result), 200 if result else 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@testing.route("/zoho/contact/email", methods=["GET"])
def get_contact_by_email():
    try:
        email = request.args.get('email')
        client_id = request.args.get('client')
        
        if not email or not client_id:
            return jsonify({'error': 'Missing required parameters: email, client'}), 400

        credentials = db.session.query(ZohoCredentials).filter_by(
            client_id=client_id
        ).first()
        
        if not credentials:
            return jsonify({'error': 'No Zoho credentials found for this client'}), 404

        zoho_manager = ZohoAPIManager(credentials)
        result = zoho_manager.get_contact_by_email(email)
        
        return jsonify(result), 200 if result else 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@testing.route("/zoho/contact", methods=["POST"])
def create_contact():
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['contact', 'client']):
            return jsonify({'error': 'Missing required fields: contact, client'}), 400

        credentials = db.session.query(ZohoCredentials).filter_by(
            client_id=data['client']
        ).first()
        
        if not credentials:
            return jsonify({'error': 'No Zoho credentials found for this client'}), 404

        zoho_manager = ZohoAPIManager(credentials)
        result = zoho_manager.create_contact(data['contact'])
        
        return jsonify(result), 200

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

@testing.route("/zoho/deal/<deal_id>", methods=["GET"])
def get_deal_by_id(deal_id):
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
        result = zoho_manager.get_deal_by_deal_id(deal_id)
        
        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@testing.route("/zoho/deal", methods=["POST"])
def create_deal():
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['deal', 'client']):
            return jsonify({'error': 'Missing required fields: deal, client'}), 400

        credentials = db.session.query(ZohoCredentials).filter_by(
            client_id=data['client']
        ).first()
        
        if not credentials:
            return jsonify({'error': 'No Zoho credentials found for this client'}), 404

        zoho_manager = ZohoAPIManager(credentials)
        result = zoho_manager.create_deal(data['deal'])
        
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
