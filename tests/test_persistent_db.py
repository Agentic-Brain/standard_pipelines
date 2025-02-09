import pytest
from flask_security.utils import hash_password
from standard_pipelines.auth.models import User
from standard_pipelines.data_flow.models import Client, DataFlow, ClientDataFlowJoin
from standard_pipelines.extensions import db
import uuid
from test_auth import create_client_util


@pytest.fixture(scope="session")
def persistent_db(app):
    """Creates a persistent database setup with client, user, and dataflow"""
    with app.app_context():
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
        
        # Create DataFlow registry item
        data_flow = DataFlow(
            name="test_flow",
            description="Test data flow for persistent tests",
            version="1.0.0"
        )
        db.session.add(data_flow)
        db.session.commit()  # Commit to get data_flow.id
        db.session.refresh(data_flow)  # Refresh to ensure we have the ID
        db.session.refresh(client)  # Refresh client object as well
        
        # Create relationship using SQLAlchemy's relationship methods
        client.data_flows.append(data_flow)
        db.session.commit()
        
        return {
            'client': client,
            'user': user,
            'data_flow': data_flow
        }


def test_persistent_database_setup(app, persistent_db):
    """Test that persistent database items are created and retrievable"""
    client = persistent_db['client']
    user = persistent_db['user']
    data_flow = persistent_db['data_flow']
    
    with app.app_context():
        # Verify client exists and relationships
        retrieved_client = Client.query.get(client.id)
        assert retrieved_client is not None
        assert retrieved_client.name == client.name
        
        # Verify user exists and is linked to client
        retrieved_user = User.query.filter_by(client_id=client.id).first()
        assert retrieved_user is not None
        assert retrieved_user.email == user.email
        
        # Verify dataflow exists and is linked to client
        retrieved_data_flow = DataFlow.query.get(data_flow.id)
        assert retrieved_data_flow is not None
        assert retrieved_data_flow.name == data_flow.name
        assert client.id in [c.id for c in retrieved_data_flow.clients]
