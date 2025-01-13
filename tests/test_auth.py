import pytest
from flask_security.utils import hash_password
from flask_base.auth.models import User, Role, UserRoleJoin
from flask_base.extensions import db
import uuid



def test_create_user(app):
    """Test user creation and retrieval"""
    user = app.user_datastore.create_user(
        email="test@example.com",
        password=hash_password("password123"),
        active=True,
        fs_uniquifier=str(uuid.uuid4())
    )
    db.session.commit()

    retrieved_user = app.user_datastore.find_user(email="test@example.com")
    assert retrieved_user is not None
    assert retrieved_user.email == "test@example.com"
    assert retrieved_user.active is True

def test_create_role(app):
    """Test role creation and retrieval"""
    role = app.user_datastore.create_role(
        name="admin",
        description="Administrator role"
    )
    db.session.commit()

    retrieved_role = app.user_datastore.find_role("admin")
    assert retrieved_role is not None
    assert retrieved_role.name == "admin"
    assert retrieved_role.description == "Administrator role"

def test_user_role_assignment(app):
    """Test assigning roles to users"""
    # Create user and role
    user = app.user_datastore.create_user(
        email="test_role@example.com",
        password=hash_password("password123"),
        active=True,
        fs_uniquifier=str(uuid.uuid4())
    )
    role = app.user_datastore.create_role(
        name="test_role",
        description="Test role"
    )
    db.session.commit()

    # Assign role to user
    app.user_datastore.add_role_to_user(user, role)
    db.session.commit()

    # Verify assignment
    retrieved_user = app.user_datastore.find_user(email="test_role@example.com")
    assert retrieved_user is not None
    assert len(retrieved_user.roles) == 1
    assert retrieved_user.roles[0].name == "test_role"

def test_user_authentication(client):
    """Test user login functionality"""
    # Create test user
    user = client.application.user_datastore.create_user(
        email="register_test@gmail.com",
        password=hash_password("password123"),
        active=True,
        fs_uniquifier=str(uuid.uuid4())
    )
    db.session.commit()

    # Test login
    response = client.post('/login', data={
        'email': 'register_test@gmail.com',
        'password': 'password123',
        'remember': 'true'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # Verify user is logged in
    user = client.application.user_datastore.find_user(email="register_test@gmail.com")
    assert user is not None
    assert user.login_count > 0
    assert user.current_login_ip is not None

def test_user_registration(client):
    """Test user registration endpoint"""
    response = client.post('/register', data={
        'email': 'register_test@gmail.com',
        'password': 'Password123!',
        'password_confirm': 'Password123!'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # Verify user was created
    user = client.application.user_datastore.find_user(email="register_test@gmail.com")
    assert user is not None
    
    # If using confirmable, confirm the user
    if not user.active:
        client.application.user_datastore.activate_user(user)
        db.session.commit()
    
    assert user.active is True

def test_cascade_delete(app):
    """Test that deleting a user also removes their role assignments"""
    # Create user and role
    user = app.user_datastore.create_user(
        email="cascade_test@example.com",
        password=hash_password("password123"),
        active=True,
        fs_uniquifier=str(uuid.uuid4())
    )
    role = app.user_datastore.create_role(
        name="cascade_role",
        description="Test role for cascade delete"
    )
    db.session.commit()

    # Assign role to user
    app.user_datastore.add_role_to_user(user, role)
    db.session.commit()

    # Verify join table entry exists
    join_entry = UserRoleJoin.query.filter_by(user_id=user.id).first()
    assert join_entry is not None

    # Delete user
    app.user_datastore.delete_user(user)
    db.session.commit()

    # Verify join table entry was deleted
    join_entry = UserRoleJoin.query.filter_by(user_id=user.id).first()
    assert join_entry is None

    # Verify role still exists
    retrieved_role = app.user_datastore.find_role("cascade_role")
    assert retrieved_role is not None 