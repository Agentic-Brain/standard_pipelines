from flask import Blueprint, Flask

gmail = Blueprint('gmail', __name__, url_prefix='/api/gmail')

def init_app(app: Flask):
    app.logger.debug(f'Initializing blueprint {__name__}')
    

from . import routes