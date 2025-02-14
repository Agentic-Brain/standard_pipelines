from flask import Blueprint, Flask

testing = Blueprint('testing', __name__, url_prefix='/test')

def init_app(app: Flask):
    app.logger.debug(f'Initializing blueprint {__name__}')
    # Add any testing-specific initialization here

from . import routes, gmail_api
