import pytest
from flask_security.utils import hash_password
from standard_pipelines.auth.models import User
from standard_pipelines.data_flow.models import Client, DataFlow, ClientDataFlowJoin
from standard_pipelines.extensions import db
import uuid
from tests.test_auth import create_client_util


@pytest.fixture(scope="session")
def persistent_db(app):
    """Creates a persistent database setup with client, user, and dataflow"""
    # Create client using existing utility
    client = create_client_util()
    
    # Create user with default values from config
    user = app.user_datastore.create_user(
        email="persistent_test@example.com",
        password=hash_password(app.config['DEFAULT_ADMIN_PASSWORD']),
        active=True,
        fs_uniquifier=str(uuid.uuid4()),
        client_id=client.id
    )
    db.session.commit()  # Commit user to get its ID
    
    # Create DataFlow registry item
    data_flow = DataFlow(
        name="test_flow",
        description="Test data flow for persistent tests",
        version="1.0.0"
    )
    db.session.add(data_flow)
    db.session.commit()  # Commit to get data_flow.id
    
    # Create relationship using SQLAlchemy's relationship methods
    client = Client.query.get(client.id)  # Get fresh client from DB
    data_flow = DataFlow.query.get(data_flow.id)  # Get fresh data_flow from DB
    client.data_flows.append(data_flow)
    db.session.commit()
    
    # Return the IDs instead of objects to avoid detached instance issues
    return {
        'client_id': client.id,
        'user_id': user.id,
        'data_flow_id': data_flow.id
    }


def test_persistent_database_setup(app, persistent_db):
    """Test that persistent database items are created and retrievable"""
    client_id = persistent_db['client_id']
    user_id = persistent_db['user_id']
    data_flow_id = persistent_db['data_flow_id']
    
    # Verify client exists and relationships
    client = Client.query.get(client_id)
    assert client is not None
    assert client.name == "agentic_brain"  # From create_client_util
    
    # Verify user exists and is linked to client
    user = User.query.filter_by(client_id=client_id).first()
    assert user is not None
    assert user.email == "persistent_test@example.com"
    
    # Verify dataflow exists and is linked to client
    data_flow = DataFlow.query.get(data_flow_id)
    assert data_flow is not None
    assert data_flow.name == "test_flow"
    assert client_id in [c.id for c in data_flow.clients]
