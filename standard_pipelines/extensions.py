from flask_sqlalchemy import SQLAlchemy
from flask_security.core import Security
from flask_migrate import Migrate
from flask_mail import Mail
from flask_admin import Admin

db = SQLAlchemy()
security = Security()
migrate = Migrate()
mail = Mail()
# NAME: Update 'server' to actual app name
admin = Admin(name='server')