import os
import sys
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from standard_pipelines import create_app
from standard_pipelines.extensions import db
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer



postgres = PostgresContainer("postgres:16-alpine")
redis = RedisContainer("redis:7-alpine")

@pytest.fixture(scope='session')
def app(request):
    """Create and configure a new app instance for all tests in module."""
    postgres.start()
    redis.start()
    
    # Set base testing environment variables
    os.environ['FLASK_ENV'] = 'testing'
    os.environ["TESTING_DB_HOST"] = postgres.get_container_host_ip()
    os.environ["TESTING_DB_PORT"] = str(postgres.get_exposed_port(5432))
    os.environ["TESTING_DB_USER"] = postgres.username
    os.environ["TESTING_DB_PASS"] = postgres.password
    os.environ["TESTING_DB_NAME"] = postgres.dbname
    os.environ["TESTING_REDIS_HOST"] = redis.get_container_host_ip()
    os.environ["TESTING_REDIS_PORT"] = str(redis.get_exposed_port(6379))
    redis_url = f"redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}/0"
    os.environ['TESTING_BROKER_URL'] = redis_url
    os.environ['TESTING_RESULT_BACKEND'] = redis_url
    
    # Create the app with the test configuration
    app = create_app()
    
    # Configure API usage based on the application's config
    for api_flag, enabled in app.config['API_USE_SETTINGS'].items():
        # TEST: This enabled may always be true
        env_var = f'TESTING_{api_flag}'
        os.environ[env_var] = str(enabled)
        
        if enabled:
            # If the API is enabled, copy over the relevant API settings from the app config
            api_group = app.config['API_SETTINGS'].get(api_flag)
            if api_group:
                for key in app.config.API_SETTINGS.get(api_group, {}):
                    env_key = f'TESTING_{key}'
                    config_value = getattr(app.config, key, None)
                    if config_value is not None:
                        os.environ[env_key] = str(config_value)
        else:
            # If the API is not enabled, set the environment variable to an empty string
            app.logger.info(f"Skipping {api_flag} API tests")
    
    def remove_containers():
        postgres.stop()
        redis.stop()
    
    request.addfinalizer(remove_containers)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture(scope='module')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='module')
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture(autouse=True)
def cleanup(app):
    """Cleanup after each test"""
    yield
    db.session.remove()
    db.engine.dispose()

@pytest.fixture(scope='session')
def celery_app(app):
    """Create a Celery app instance for testing."""
    return app.extensions['celery']