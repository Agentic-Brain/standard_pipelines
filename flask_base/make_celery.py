from flask import Flask
from flask_base import create_app

flask_app: Flask = create_app()
celery_app = flask_app.extensions["celery"]
