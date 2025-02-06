from flask import Blueprint

api = Blueprint('api', __name__)

def init_app(app):
    app.logger.debug(f'Initializing blueprint {__name__}')
