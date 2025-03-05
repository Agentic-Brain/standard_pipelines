from flask import Flask
import os
import socket
from standard_pipelines.version import APP_VERSION, FLASK_BASE_VERSION
from dotenv import load_dotenv
import logging
import colorlog
import time
from logging.handlers import SysLogHandler
from standard_pipelines.extensions import migrate, db
from typing import Optional
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from standard_pipelines.config import DevelopmentConfig, ProductionConfig, TestingConfig, StagingConfig, get_config
from standard_pipelines.data_flow.utils import BaseDataFlow
from standard_pipelines.data_flow.ff2hs_on_transcript.services import FF2HSOnTranscript
from standard_pipelines.data_flow.gmail_interval_followup.services import GmailIntervalFollowup



def create_app():
    load_dotenv()
    load_dotenv('.flaskenv')
    init_sentry()
    app = Flask(__name__)
    
    # Initialize basic logging first
    init_basic_logging(app)
    
    environment_type: Optional[str] = os.getenv('FLASK_ENV')
    config = None
    
    if environment_type is None:
        app.logger.critical('NO ENVIRONMENT TYPE DEFINED, ABORTING')
        quit()
    elif environment_type == 'development':
        config = DevelopmentConfig()
        app.logger.setLevel(logging.DEBUG)
    elif environment_type == 'production':
        config = ProductionConfig()
    elif environment_type == 'testing':
        config = TestingConfig()
    elif environment_type == 'staging':
        config = StagingConfig()
    else:
        app.logger.critical('INVALID ENVIRONMENT TYPE DEFINED, ABORTING')
        quit()

    app.config.from_object(config)
    
    # Initialize Papertrail logging after config is loaded
    init_papertrail_logging(app)
    
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

    # Add the new API blueprint registration
    from .api import api as api_blueprint
    from .api import init_app as api_init_app
    app.register_blueprint(api_blueprint)
    api_init_app(app)

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
    
    from .celery import init_app as celery_init_app
    celery_init_app(app)

    # Register testing blueprint only in development or testing environments
    if environment_type in ['development', 'testing']:
        from .testing import testing as testing_blueprint
        from .testing import init_app as testing_init_app
        app.register_blueprint(testing_blueprint)
        testing_init_app(app)

    @app.context_processor
    def inject_semver():
        return dict(app_version=str(APP_VERSION), flask_base_version=str(FLASK_BASE_VERSION))


    return app

def init_basic_logging(app: Flask) -> None:
    """Initialize basic logging without config-dependent features"""
    # Clear ALL handlers (including Flask's default handlers)
    app.logger.handlers.clear()
    logging.getLogger().handlers.clear()

    # Set the logger level
    app.logger.setLevel(logging.INFO)
    
    # Create logs directory if it doesn't exist
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    environment_type = os.getenv('FLASK_ENV', 'development')
    
    # Define format based on environment
    if environment_type == 'production':
        log_format = '%(asctime)s - %(levelname)s : %(message)s'
        date_format = '%y-%m-%d %H:%M'
    elif environment_type == 'development':
        log_format = '%(filename)s:%(lineno)d - %(levelname)s : %(message)s'
        date_format = None
    else:  # staging
        log_format = '%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s : %(message)s'
        date_format = '%y-%m-%d %H:%M'

    # File handler with environment-specific format
    file_handler = logging.FileHandler(f'logs/{str(time.ctime(time.time()))}.log')
    file_formatter = logging.Formatter(log_format, datefmt=date_format)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Stream handler with color
    stream_handler = logging.StreamHandler()
    stream_formatter = colorlog.ColoredFormatter(
        '%(log_color)s' + log_format + '%(reset)s',
        datefmt=date_format,
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
    
    # Prevent propagation to avoid duplicate logs
    app.logger.propagate = False

def init_papertrail_logging(app: Flask) -> None:
    """Initialize Papertrail logging after config is loaded"""
    papertrail_host = app.config.get('PAPERTRAIL_HOST')
    papertrail_port = app.config.get('PAPERTRAIL_PORT')
    
    papertrail_system_hostname = app.config.get('PAPERTRAIL_SYSTEM_HOSTNAME')
    app_name = app.config.get('FLASK_APP')
    
    # TODO: Need to set flask app to be read from .flaskenv
    # current system doesnt work because it isnt prefixed by environment type
    if all([papertrail_host, papertrail_port, app_name]):
        try:
            class ContextFilter(logging.Filter):
                hostname = socket.gethostname()
                def filter(self, record):
                    record.hostname = ContextFilter.hostname
                    return True
                
            papertrail_handler = SysLogHandler(address=(papertrail_host, int(papertrail_port)))
            papertrail_handler.addFilter(ContextFilter())
            
            papertrail_format = f'%(asctime)s {papertrail_system_hostname} {app_name}: %(levelname)s [%(filename)s:%(lineno)d] %(message)s'
            papertrail_formatter = logging.Formatter(papertrail_format, datefmt='%b %d %H:%M:%S')
            papertrail_handler.setFormatter(papertrail_formatter)
            
            papertrail_handler.setLevel(logging.DEBUG)
            
            app.logger.addHandler(papertrail_handler)
            app.logger.info("Papertrail logging configured")
        except Exception as e:
            app.logger.error(f"Failed to initialize Papertrail logging: {str(e)}")
    else:
        app.logger.warning("Papertrail logging not configured - missing required settings")

def init_sentry() -> None:
    config = get_config()
    sentry_sdk.init(
        dsn=config.SENTRY_DSN, #type: ignore
        integrations=[FlaskIntegration(), CeleryIntegration()],
        environment=str(os.getenv('FLASK_ENV')),
        release=APP_VERSION if APP_VERSION else FLASK_BASE_VERSION,
        traces_sample_rate=1.0,
        send_default_pii=True,
        profiles_sample_rate=1.0,
        _experiments = {
            "continuous_profiling_auto_start": True,
        }
    )
