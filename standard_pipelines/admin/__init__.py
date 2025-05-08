from flask import Blueprint, Flask
from typing import Dict, List, Type, Optional, Any, Callable

# Create the blueprint
admin = Blueprint('admin', __name__, url_prefix='/admin')

# Store registered views globally
_registered_views = []
_view_categories = {}


def init_app(app: Flask):
    """Initialize the custom admin blueprint with the Flask application"""
    app.logger.debug(f'Initializing blueprint {__name__}')
    
    # Register custom context processors
    @app.context_processor
    def inject_admin_data():
        return {
            'admin_views': _registered_views,
            'admin_categories': _view_categories
        }
    
    # Register example models
    from .example import register_admin_models
    with app.app_context():
        register_admin_models()

def register_view(view):
    """Register a view with the custom admin"""
    _registered_views.append(view)
    
    # Organize views by category
    category = view.category
    if category:
        if category not in _view_categories:
            _view_categories[category] = []
        _view_categories[category].append(view)
    
    return view

# Import routes at the end to avoid circular imports
from . import routes