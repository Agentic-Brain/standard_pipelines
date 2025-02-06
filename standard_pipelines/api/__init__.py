from flask import Blueprint, Flask

api = Blueprint('api', __name__, url_prefix='/api')

def init_app(app: Flask):
    app.logger.debug(f'Initializing blueprint {__name__}')
    

    # Add any API-specific initialization here
    # For example, registering error handlers, before_request handlers, etc.
    

from .fireflies import routes as fireflies_routes
from .hubspot import routes as hubspot_routes