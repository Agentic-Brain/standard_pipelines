from flask import Flask
from standard_pipelines import create_app

flask_app: Flask = create_app()
celery_app = flask_app.extensions["celery"]
