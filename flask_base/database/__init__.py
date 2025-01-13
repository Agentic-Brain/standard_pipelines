from flask import Blueprint, Flask
from flask_base.extensions import db

database = Blueprint('database', __name__)

def init_app(app: Flask):
    app.logger.debug(f'Initalizing blueprint {__name__}')
    db.init_app(app)
    
from flask_base.database.models import *