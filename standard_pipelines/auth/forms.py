from flask_security.forms import RegisterForm
from wtforms import HiddenField, validators

class CustomRegisterForm(RegisterForm):
    """Custom registration form that includes client_id."""
    client_id = HiddenField('Client ID', [validators.DataRequired()])
