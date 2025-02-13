
from flask import Flask, request, jsonify
from hubspot.files import ApiException
from datetime import datetime, timedelta
from standard_pipelines.database.models import ScheduledMixin
from standard_pipelines.extensions import db

# Be sure to import your HubSpotAPIManager and any needed exceptions
# from the module where you defined it.
from standard_pipelines.api.hubspot.services import HubSpotAPIManager
from standard_pipelines.data_flow.exceptions import APIError
from . import testing


# Example config for HubSpot – fill these with your actual values or load from env
HUBSPOT_CONFIG = {
    "client_id": "",  # Will be provided per request
    "client_secret": "",  # Will be provided per request
    "refresh_token": ""  # Will be provided per request
}

# Create manager instance per request with provided credentials
def get_hubspot_manager(client_id: str) -> HubSpotAPIManager:
    """Get a HubSpot manager instance with credentials for the given client."""
    # In a real implementation, we would fetch credentials from the database
    # For testing purposes, we'll use empty credentials
    config = HUBSPOT_CONFIG.copy()
    return HubSpotAPIManager(config)

@testing.route("/create-contact", methods=["POST"])
def test_create_contact():
    """
    Expects a JSON body with optional "email", "first_name", "last_name".
    Example:
      {
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe"
      }
    """
    data = request.get_json(force=True)

    email = data.get("email")
    first_name = data.get("first_name")
    last_name = data.get("last_name")

    try:
        contact = hubspot_manager.create_contact(
            email=email,
            first_name=first_name,
            last_name=last_name
        )
    except (ApiException, APIError) as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(contact), 201

@testing.route("/create-deal", methods=["POST"])
def test_create_deal():
    """
    Expects a JSON body with required "deal_name" and "contact_id".
    Example:
      {
        "deal_name": "My Test Deal",
        "contact_id": "123456789"  # The internal HubSpot contact ID
      }
    """
    data = request.get_json(force=True)
    deal_name = data.get("deal_name")
    # contact_id = data.get("contact_id")

    # if not deal_name or not contact_id:
    #     return jsonify({"error": "Must provide 'deal_name' and 'contact_id'"}), 400

    try:
        deal = hubspot_manager.create_deal(deal_name)
    except (ApiException, APIError) as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(deal), 201


@testing.route("/create-meeting", methods=["POST"])
def test_create_meeting():
    """
    Expects a JSON body that matches the structure needed by create_meeting:
      {
        "properties": {
            "hs_timestamp": "2023-01-01T12:00:00.000Z",
            "hubspot_owner_id": "...",
            "hs_meeting_title": "Meeting Title",
            "hs_meeting_body": "Optional meeting description",
            "hs_internal_meeting_notes": "Some notes",
            "hs_meeting_location": "Remote",
            "hs_meeting_start_time": "2023-01-01T12:00:00.000Z",
            "hs_meeting_outcome": "COMPLETED"
        },
        "associations": [
            {
                "to": {"id": "1234567"},
                "types": [
                  {
                    "associationCategory": "HUBSPOT_DEFINED",
                    "associationTypeId": 200
                  }
                ]
            },
            ...
        ]
      }
    """
    meeting_data = request.get_json(force=True)
    try:
        hubspot_manager.create_meeting(meeting_data)
    except (ApiException, APIError) as e:
        return jsonify({"error": str(e)}), 400
    
    return jsonify({"message": "Meeting created"}), 201


@testing.route("/create-note", methods=["POST"])
def test_create_note():
    """
    Expects a JSON body that matches the structure needed by create_note:
      {
        "properties": {
            "hs_timestamp": "2023-01-01T12:00:00.000Z",
            "hs_note_body": "This is my note",
            "hubspot_owner_id": "...",
        },
        "associations": [
            {
                "to": {"id": "9876543"},
                "types": [
                  {
                    "associationCategory": "HUBSPOT_DEFINED",
                    "associationTypeId": 214
                  }
                ]
            }
        ]
      }
    """
    note_data = request.get_json(force=True)
    try:
        hubspot_manager.create_note(note_data)
    except (ApiException, APIError) as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"message": "Note created"}), 201

@testing.route("/test/deal/<client_id>/<deal_id>", methods=["GET"])
def test_get_deal(client_id: str, deal_id: str):
    """Get a deal by ID with all properties."""
    try:
        manager = get_hubspot_manager(client_id)
        deal = manager.deal_by_deal_id(deal_id)
        return jsonify(deal), 200
    except (ApiException, APIError) as e:
        return jsonify({"error": str(e)}), 400

@testing.route("/test/deal/<client_id>/<deal_id>/notes", methods=["GET"])
def test_get_deal_notes(client_id: str, deal_id: str):
    """Get all notes associated with a deal."""
    try:
        manager = get_hubspot_manager(client_id)
        notes = manager.get_deal_notes(deal_id)
        return jsonify(notes), 200
    except (ApiException, APIError) as e:
        return jsonify({"error": str(e)}), 400

@testing.route("/test/deal/<client_id>/<deal_id>/items", methods=["GET"])
def test_get_deal_items(client_id: str, deal_id: str):
    """Get all engagement items associated with a deal."""
    try:
        manager = get_hubspot_manager(client_id)
        items = manager.get_deal_items(deal_id)
        return jsonify(items), 200
    except (ApiException, APIError) as e:
        return jsonify({"error": str(e)}), 400

@testing.route("/deal-flow", methods=["POST"])
def test_deal_flow():
    """
    Tests the full flow of creating a contact and an associated deal.
    Expects a JSON body with:
    {
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "deal_name": "Test Deal 123"
    }
    """
    data = request.get_json(force=True)
    
    if not data.get("email") or not data.get("deal_name"):
        return jsonify({"error": "Must provide at least 'email' and 'deal_name'"}), 400

    try:
        # First create the contact
        contact = hubspot_manager.create_contact(
            email=data.get("email"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name")
        )
        
        # Get the contact ID from the response
        contact_id = contact.get("id")
        if not contact_id:
            return jsonify({"error": "Failed to get contact ID from response"}), 500
            
        # Create the deal with the contact association
        # TODO: Get the stage id dynamically, cant hardcode this
        deal = hubspot_manager.create_deal(
            deal_name=data.get("deal_name"),
            stage_id="995768441",
            contact_id=contact_id
        )
        
        return jsonify({
            "success": True,
            "contact": contact,
            "deal": deal
        }), 201
        
    except (ApiException, APIError) as e:
        return jsonify({"error": str(e)}), 400
