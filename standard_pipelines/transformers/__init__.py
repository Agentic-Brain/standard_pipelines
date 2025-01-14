from flask import Blueprint, Flask
from standard_pipelines.extensions import db

transformers = Blueprint('transformers', __name__)

def init_app(app: Flask) -> None:
    """Initialize the transformers blueprint"""
    app.logger.debug(f'Initializing blueprint {__name__}')
    
    # Import models here to avoid circular imports
    # from flask_base.transformers import models
    
    # Import routes after models
    # from . import routes 