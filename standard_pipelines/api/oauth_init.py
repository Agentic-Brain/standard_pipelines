"""
Initialize the OAuth system and register all OAuth routes.
"""
from flask import Flask
from standard_pipelines.api.oauth_system import register_oauth_clients, create_oauth_routes
from standard_pipelines.api.oauth_discovery import ensure_oauth_models_loaded


def init_oauth_system(app: Flask):
    """Initialize the OAuth system with the Flask app."""
    
    # Discover and load all OAuth credential models
    # This automatically triggers registration via the metaclass
    ensure_oauth_models_loaded()
    
    # Register OAuth clients
    register_oauth_clients(app)
    
    # Create and register OAuth routes
    oauth_bp = create_oauth_routes()
    app.register_blueprint(oauth_bp)
    
    app.logger.info("OAuth system initialized successfully")