import pytest

def test_database_blueprint_initialization(app):
    """Test that the database blueprint is properly registered"""
    assert 'database' in app.blueprints
    database_bp = app.blueprints['database']
    assert database_bp.name == 'database'

def test_auth_blueprint_initialization(app):
    """Test that the auth blueprint is properly registered"""
    assert 'auth' in app.blueprints
    auth_bp = app.blueprints['auth']
    assert auth_bp.name == 'auth'

def test_main_blueprint_initialization(app):
    """Test that the main blueprint is properly registered"""
    assert 'main' in app.blueprints
    main_bp = app.blueprints['main']
    assert main_bp.name == 'main'

def test_admin_dash_blueprint_initialization(app):
    """Test that the admin_dash blueprint is properly registered"""
    assert 'admin_dash' in app.blueprints
    admin_bp = app.blueprints['admin_dash']
    assert admin_bp.name == 'admin_dash'