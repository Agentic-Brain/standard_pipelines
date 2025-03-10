from flask_sqlalchemy import SQLAlchemy
from flask_security.core import Security
from flask_migrate import Migrate
from flask_mail import Mail
from flask_admin import Admin
from authlib.integrations.flask_client import OAuth

db : SQLAlchemy = SQLAlchemy()
security : Security = Security()
migrate : Migrate = Migrate()
mail : Mail = Mail()
# NAME: Update 'server' to actual app name
admin : Admin = Admin(name='server')
oauth : OAuth = OAuth()
