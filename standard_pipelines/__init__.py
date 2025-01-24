from flask import Flask, request
from sqlalchemy import func
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel
from flask_security.utils import hash_password
import os
from standard_pipelines.version import APP_VERSION, FLASK_BASE_VERSION
from dotenv import load_dotenv
import logging
import colorlog
import time
from standard_pipelines.extensions import migrate, db
from typing import Optional
import sentry_sdk
from standard_pipelines.config import DevelopmentConfig, ProductionConfig, TestingConfig, Config, get_config
from standard_pipelines.data_flow.models import Client, DataFlowRegistry
from standard_pipelines.auth.models import User

def create_app():
    load_dotenv()
    load_dotenv('.flaskenv')
    init_sentry()
    app = Flask(__name__)
    environment_type: Optional[str] = os.getenv('FLASK_ENV')
    config = None
    init_logging(app)
    if environment_type is None:
        app.logger.critical('NO ENVIRONMENT TYPE DEFINED, ABORTING')
        quit()
    elif environment_type == 'development':
        config = DevelopmentConfig()
        app.logger.setLevel(logging.DEBUG)
        # app.logger.debug('Server config initialized', str(config.__dict__))
    elif environment_type == 'production':
        config = ProductionConfig()
    elif environment_type == 'testing':  # Add this block
        config = TestingConfig()
    else:
        app.logger.critical('INVALID ENVIRONMENT TYPE DEFINED, ABORTING')
        quit()

    app.config.from_object(config)
    migrate.init_app(app, db)
    

    # Init requirements for blueprints
    from .cli import init_app as cli_init_app
    cli_init_app(app)

    from .database import database as database_blueprint
    from .database import init_app as database_init_app
    app.register_blueprint(database_blueprint)
    database_init_app(app)

    from .auth import auth as auth_blueprint
    from .auth import init_app as auth_init_app
    app.register_blueprint(auth_blueprint)
    auth_init_app(app)

    from .data_flow import data_flow as data_flow_blueprint
    from .data_flow import init_app as data_flow_init_app
    app.register_blueprint(data_flow_blueprint)
    data_flow_init_app(app)

    from .main import main as main_blueprint
    from .main import init_app as main_init_app
    app.register_blueprint(main_blueprint)
    main_init_app(app)

    from .admin_dash import admin_dash as admin_dash_blueprint
    from .admin_dash import init_app as admin_dash_init_app
    app.register_blueprint(admin_dash_blueprint)
    # admin_dash_init_app(app)

    from .api.gmail import gmail as gmail_blueprint
    from .api.gmail import init_app as gmail_init_app
    app.register_blueprint(gmail_blueprint)
    gmail_init_app(app)
    
    from .celery import init_app as celery_init_app
    celery_init_app(app)

    @app.context_processor
    def inject_semver():
        return dict(app_version=str(APP_VERSION), flask_base_version=str(FLASK_BASE_VERSION))
    # Migrate must be in server init function to work
    # migrate.init_app(app, database)


    
    # TODO: move into seperate blueprint?
    # Admin setup

    return app

def init_logging(app: Flask) -> None:
    # Clear existing handlers
    app.logger.handlers.clear()

    # Set the logger level
    app.logger.setLevel(logging.INFO)

    # Create logs directory if it doesn't exist
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # File handler
    file_handler = logging.FileHandler(f'logs/{str(time.ctime(time.time()))}.log')
    file_formatter = logging.Formatter('%(asctime)s %(filename)s - %(funcName)s - %(lineno)d - %(name)s - %(levelname)s : %(message)s')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Stream handler with color
    stream_handler = logging.StreamHandler()
    stream_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)s - %(name)s:%(reset)s %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    stream_handler.setFormatter(stream_formatter)

    # Add handlers to app.logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(stream_handler)


def init_sentry() -> None:
    config = get_config()
    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        environment=str(os.getenv('FLASK_ENV')),
        release=APP_VERSION if APP_VERSION else FLASK_BASE_VERSION,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        _experiments = {
            "continuous_profiling_auto_start": True,
        }
    )