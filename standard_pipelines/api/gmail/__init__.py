from flask import Blueprint, Flask
import os

gmail = Blueprint('gmail', __name__, url_prefix='/api/gmail')

if os.getenv('FLASK_ENV', 'development').lower() == 'development' or os.getenv('FLASK_ENV', 'testing').lower() == 'testing':
    # Allows HTTP for local development
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  


def init_app(app: Flask):
    app.logger.debug(f'Initializing blueprint {__name__}')    

from . import routes