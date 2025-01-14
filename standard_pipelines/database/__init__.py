from flask import Blueprint, Flask
from standard_pipelines.extensions import db

database = Blueprint('database', __name__)

def init_app(app: Flask):
    app.logger.debug(f'Initalizing blueprint {__name__}')
    db.init_app(app)
    
from standard_pipelines.database.models import *