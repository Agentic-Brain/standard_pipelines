"""Routes for the data_flow blueprint."""
from flask import current_app
from . import data_flow  # Import the blueprint

@data_flow.route('/')
def index():
    """Default route for data flow."""
    return "Data Flow Index"
