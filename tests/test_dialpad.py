import pytest
from standard_pipelines.api.dialpad.services import DialpadAPIManager
from standard_pipelines.api.dialpad.models import DialpadCredentials
from uuid import uuid4

def test_dialpad_credentials():
    client_id = uuid4()
    api_key = "test-api-key"
    creds = DialpadCredentials(client_id=client_id, dialpad_api_key=api_key)
    assert creds.client_id == client_id
    assert creds.dialpad_api_key == api_key

def test_dialpad_api_manager():
    manager = DialpadAPIManager({"api_key": "test-key"})
    assert manager.required_config == ["api_key"]
    assert manager.api_url({"call_id": "123"}) == "https://dialpad.com/api/v2/transcripts/123"
    
    with pytest.raises(ValueError):
        manager.api_url()  # Should raise error when call_id missing

def test_dialpad_authenticator():
    manager = DialpadAPIManager({"api_key": "test-key"})
    auth = manager.authenticator()
    headers = {}
    auth(type("Request", (), {"headers": headers}))
    assert headers["Authorization"] == "Bearer test-key"

def test_dialpad_blueprint_initialization(app):
    """Test that the dialpad blueprint is properly registered"""
    assert 'dialpad' in app.blueprints
    dialpad_bp = app.blueprints['dialpad']
    assert dialpad_bp.name == 'dialpad'
