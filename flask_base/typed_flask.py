from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_security.core import Security
from flask_migrate import Migrate
from flask_mail import Mail
from flask_admin import Admin

class TypedFlask(Flask):
    pass