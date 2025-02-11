from dotenv import load_dotenv
import os
from typing import Any, Dict
from standard_pipelines.version import get_versions
# TODO: Should shift this from warnings to logging
import warnings

class Config:
    # Core settings that are required for the application to function
    REQUIRED_SETTINGS: Dict[str, Any] = {
        'DB_USER': None,
        'DB_PASS': None,
        'DB_HOST': None,
        'DB_PORT': None,
        'DB_NAME': None,
        'REDIS_HOST': None,
        'REDIS_PORT': 6379,
        'REDIS_DB': 0,
        'SECRET_KEY': None,
        'ENCRYPTION_KEY': None,
        'SECURITY_PASSWORD_SALT': None,
        'SECURITY_PASSWORD_HASH': 'bcrypt',
        'DEFAULT_CLIENT_NAME': 'agentic-brain',
        'INTERNAL_API_KEY': None,
    }

    # Optional settings that enable additional features
    OPTIONAL_SETTINGS: Dict[str, Any] = {
        'EMAIL_HTML': True,
        'DEFAULT_ADMIN_ACCOUNT': None,
        'DEFAULT_ADMIN_PASSWORD': None,
        'SECURITY_REGISTERABLE': True,
        'SECURITY_CONFIRMABLE': True,
        'SECURITY_CHANGEABLE': True,
        'SECURITY_RECOVERABLE': True,
        'SECURITY_TWO_FACTOR': False,
        'SECURITY_TRACKABLE': True,
        'SENTRY_DSN': None,
    }

    # API Usage flags
    API_USE_SETTINGS: Dict[str, bool] = {
        'USE_STRIPE': False,
        'USE_BITWARDEN': True,
        'USE_GOOGLE': True,
        'USE_OPENAI': True,
        'USE_MAILGUN': True,
        'USE_HUBSPOT': True,
        # Add more API usage flags as needed
    }

    # API Configuration values
    API_SETTINGS: Dict[str, Dict[str, Any]] = {
        'STRIPE': {
            'STRIPE_SECRET_KEY': None,
            'STRIPE_PUBLIC_KEY': None,
            'STRIPE_WEBHOOK_SIGNING_KEY': None,
        },
        'BITWARDEN': {
            'BITWARDEN_ACCESS_TOKEN': None,
            'BITWARDEN_STATE_FILE_PATH': None,
            'BITWARDEN_ORGANIZATION_ID': None,
            'DEFAULT_CLIENT_BITWARDEN_KEY_ID': None,
        },
        'OPENAI': {
            'OPENAI_API_KEY': None,
        },
        'MAILGUN': {
            'MAILGUN_API_KEY': None,
            'MAILGUN_SEND_DOMAIN': None,
            'MAILGUN_SEND_USER': None,
        },
        'HUBSPOT': {
            'HUBSPOT_CLIENT_ID': None,
            'HUBSPOT_CLIENT_SECRET': None,
        },
        'GOOGLE': {
            'GOOGLE_REDIRECT_URI': None,
            'GOOGLE_CLIENT_ID': None,
            'GOOGLE_CLIENT_SECRET': None,
            'GOOGLE_SCOPES': "https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly",
        },
        # Add more API configurations as needed
    }

    # Mapping of API usage flags to their corresponding API groups
    API_REQUIREMENTS: Dict[str, str] = {
        'USE_STRIPE': 'STRIPE',
        'USE_BITWARDEN': 'BITWARDEN',
        'USE_MAILGUN': 'MAILGUN',
        'USE_GOOGLE': 'GOOGLE',
        'USE_OPENAI': 'OPENAI',
        'USE_HUBSPOT': 'HUBSPOT',
        # Add more mappings as needed
    }

    # Data flow configuration paths
    DATA_FLOW_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'data_flow')
    TAP_HUBSPOT_CONTACTS_CATALOG_PATH = os.path.join(DATA_FLOW_CONFIG_DIR, 'tap_hubspot_contacts_catalog.json')
 
    def __init__(self, env_prefix: str) -> None:
        # These are all defined just to prevent errors with type checking
        self.DB_USER: str
        self.DB_PASS: str
        self.DB_NAME: str
        self.DB_HOST: str
        self.DB_PORT: str
        self.REDIS_HOST: str
        self.REDIS_PORT: str
        
        load_dotenv()
        versions = get_versions()
        self.FLASK_BASE_VERSION = versions['flask_base']
        self.APP_VERSION = versions['app']
        self.env_prefix = env_prefix

        # Set required settings
        self._configure_settings(self.REQUIRED_SETTINGS, required=True)
        # Set optional settings
        self._configure_settings(self.OPTIONAL_SETTINGS, required=False)
        # Configure API usage flags
        self._configure_api_usage()
        # Configure API settings based on usage
        self._configure_api_settings()

        self.SQLALCHEMY_DATABASE_URI = f'postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'
        self.set_additional_config()
        self.build_celery_config()

    def _configure_settings(self, settings: Dict[str, Any], required: bool = False) -> None:
        """Configure settings from environment variables or defaults"""
        for key, common_value in settings.items():
            env_value = self.get_env(key)
            if env_value is not None:
                setattr(self, key, env_value)
            elif not hasattr(self, key) or getattr(self, key) is None:
                if required and common_value is None:
                    raise ValueError(f"Required configuration '{key}' is not set")
                setattr(self, key, getattr(self, key, common_value))

    def _configure_api_usage(self) -> None:
        """Configure which APIs are in use"""
        for api_flag in self.API_USE_SETTINGS:
            env_value = self.get_env(api_flag)
            if env_value is not None:
                # Convert string environment values to boolean
                use_api = env_value.lower() in ('true', '1', 'yes', 'on')
                setattr(self, api_flag, use_api)
            else:
                setattr(self, api_flag, self.API_USE_SETTINGS[api_flag])

    def _configure_api_settings(self) -> None:
        """Configure API-specific settings based on which APIs are in use"""
        env = os.getenv('FLASK_ENV', 'development').lower()
        is_dev_or_test = env in ['development', 'testing']
        
        for api_flag, api_group in self.API_REQUIREMENTS.items():
            if getattr(self, api_flag, False):
                # If this API is in use, configure its settings
                api_settings = self.API_SETTINGS[api_group]
                missing_configs = []
                
                for key, default_value in api_settings.items():
                    env_value = self.get_env(key)
                    if env_value is not None:
                        setattr(self, key, env_value)
                    elif default_value is not None:
                        setattr(self, key, default_value)
                    else:
                        if is_dev_or_test:
                            missing_configs.append(key)
                            setattr(self, key, None)  # Set to None for dev/test
                        else:
                            raise ValueError(
                                f"Required API configuration '{key}' is not set for {api_group}. "
                                f"This must be set via environment variable {self.env_prefix}_{key} "
                                f"when {api_flag} is enabled."
                            )
                
                if is_dev_or_test and missing_configs:
                    warnings.warn(
                        f"Warning: {api_group} is enabled but missing configurations: {', '.join(missing_configs)}. "
                        f"These should be set via environment variables in {self.env_prefix} prefix. "
                        "This warning is only shown in development/testing environments."
                    )

    def verify_api_configuration(self) -> None:
        """Verify that all required API configurations are set when their corresponding API is in use"""
        env = os.getenv('FLASK_ENV', 'development').lower()
        is_dev_or_test = env in ['development', 'testing']
        
        for api_flag, api_group in self.API_REQUIREMENTS.items():
            if getattr(self, api_flag, False):
                api_settings = self.API_SETTINGS[api_group]
                missing_configs = []
                
                for key in api_settings:
                    if getattr(self, key, None) is None:
                        if is_dev_or_test:
                            missing_configs.append(key)
                        else:
                            raise ValueError(
                                f"Missing required API configuration for {api_group}: {key}. "
                                f"This must be set when {api_flag} is enabled."
                            )
                
                if is_dev_or_test and missing_configs:
                    warnings.warn(
                        f"Warning: {api_group} is enabled but missing configurations: {', '.join(missing_configs)}. "
                        "This warning is only shown in development/testing environments."
                    )

    def verify_attributes(self) -> None:
        '''Verifies that the configuration object has all required attributes'''
        # Verify core required settings
        for name in self.REQUIRED_SETTINGS:
            if getattr(self, name) is None:
                raise ValueError(
                    f"Required configuration '{name}' is not set. "
                    f"This must be set via environment variable {self.env_prefix}_{name} "
                    f"or in the configuration class."
                )
        # Verify API configurations
        self.verify_api_configuration()

    def get_env(self, key: str, default: Any = None) -> Any:
        return os.getenv(f'{self.env_prefix}_{key}', default)

    def build_celery_config(self):
        url = f'redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0'
        celery_conf = {
            'broker_url': url,
            'result_backend': url
        }
        self.CELERY_CONFIG = celery_conf

    # Just defined to allow for children to inherit
    def set_additional_config(self) -> None:
        pass

class DevelopmentConfig(Config):
    def __init__(self) -> None:
        self.FLASK_ENV = 'development'
        # Postgres 
        self.DB_USER: str = 'postgres'
        self.DB_PASS: str = 'postgres_password'
        self.DB_HOST: str = 'localhost'
        self.DB_PORT: int = 5432
        self.DB_NAME: str = 'postgres'
        # Redis/Celery
        self.REDIS_HOST: str = 'localhost'
        self.REDIS_PORT: int = 6379
        self.REDIS_DB: int = 0
        self.SECRET_KEY: str = 'secret'
        self.BROKER_URL = "redis://localhost:6379/0"  
        self.RESULT_BACKEND = "redis://localhost:6379/0"
        self.TASK_IGNORE_RESULT = True
        self.BITWARDEN_STATE_FILE_PATH: str = 'bitwarden-state'
        # Flask
        self.SECRET_KEY: str = 'secret'
        self.FLASK_DEBUG: bool = True
        self.DEFAULT_ADMIN_ACCOUNT:  str = 'admin@example.com'
        self.DEFAULT_ADMIN_PASSWORD: str = 'password'
        self.SECURITY_PASSWORD_SALT: str = 'password_salt' # Should be random 128 bits for production systems
        self.ENCRYPTION_KEY: str = 'IduTzHtJ7mk2B/j3TzMl4XC/+NdSFAgbIcgGh7nlguc=' # Development encryption KEY. CHANGE THIS IN PRODUCTION
        self.DEFAULT_CLIENT_NAME = 'agentic-brain'
        self.INTERNAL_API_KEY: str = 'internal_api_key'
        super().__init__('DEVELOPMENT')
        
        # Required to be set manually in each config type
        self.verify_attributes()


    def set_additional_config(self) -> None:
        additional_keys = [

        ]
        for key in additional_keys:
            setattr(self, key, self.get_env(key))

class TestingConfig(Config):
    WTF_CSRF_ENABLED = False  # Disable CSRF tokens in the forms for testing
    def __init__(self) -> None:
        self.FLASK_ENV = 'testing'
        # Postgres (using SQLite for testing)
        self.DB_USER: str = 'postgres'
        self.DB_PASS: str = 'postgres_password'
        self.DB_HOST: str = 'localhost'
        self.DB_PORT: int = 5432
        self.DB_NAME: str = 'postgres'
        # Redis/Celery
        self.REDIS_HOST: str = 'localhost'
        self.REDIS_PORT: int = 6379
        self.REDIS_DB: int = 0  # Using different DB for testing
        self.BROKER_URL = "redis://localhost:6379/0"
        self.RESULT_BACKEND = "redis://localhost:6379/0"
        self.TASK_IGNORE_RESULT = True
        # Flask
        self.SECRET_KEY: str = 'test_secret'
        self.FLASK_DEBUG: bool = True
        self.DEFAULT_ADMIN_ACCOUNT: str = 'test@example.com'
        self.DEFAULT_ADMIN_PASSWORD: str = 'test_password'
        self.SECURITY_PASSWORD_SALT: str = 'test_salt'
        self.ENCRYPTION_KEY: str = 'IduTzHtJ7mk2B/j3TzMl4XC/+NdSFAgbIcgGh7nlguc='
        self.BITWARDEN_STATE_FILE_PATH: str = 'bitwarden-state'
        # Testing specific settings
        self.TESTING = True
        self.WTF_CSRF_ENABLED = False
        self.SECURITY_CONFIRMABLE = False
        self.SECURITY_SEND_REGISTER_EMAIL = False
        self.SENTRY_DSN = ''
        self.INTERNAL_API_KEY: str = 'internal_api_key'
        super().__init__('TESTING')
        self.verify_attributes()


class ProductionConfig(Config):
    def __init__(self) -> None:
        self.FLASK_ENV = 'production'
        # Has to be set after initial creation
        super().__init__('PRODUCTION')
        self.verify_attributes()


    def set_additional_config(self) -> None:
        additional_keys = [

        ]
        for key in additional_keys:
            setattr(self, key, self.get_env(key))

class StagingConfig(Config):
    def __init__(self) -> None:
        self.FLASK_ENV = 'staging'
        # Has to be set after initial creation, similar to ProductionConfig
        super().__init__('STAGING')
        self.verify_attributes()

    def set_additional_config(self) -> None:
        additional_keys = [

        ]
        for key in additional_keys:
            setattr(self, key, self.get_env(key))

# Used to get initial config type, defined by FLASK_ENV
def get_config() -> Config:
    env = os.getenv('FLASK_ENV', 'development').lower()
    config_classes = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'staging': StagingConfig,
        'production': ProductionConfig
    }
    return config_classes.get(env, DevelopmentConfig)()
