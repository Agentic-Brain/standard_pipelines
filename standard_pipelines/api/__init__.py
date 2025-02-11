from flask import Blueprint, Flask

from standard_pipelines.extensions import oauth

api = Blueprint('api', __name__, url_prefix='/api')

def init_app(app: Flask):
    app.logger.debug(f'Initializing blueprint {__name__}')
    hubspot_oauth_client_register(app)
    gmail_oauth_client_register(app)
    

    # Add any API-specific initialization here
    # For example, registering error handlers, before_request handlers, etc.
    
def gmail_oauth_client_register(app: Flask):
# TODO: Clean this up a little using dict/set checking method
    gmail_client_id = app.config.get('GMAIL_CLIENT_ID')
    gmail_client_secret = app.config.get('GMAIL_CLIENT_SECRET')
    gmail_scopes = app.config.get('GMAIL_SCOPES')
    gmail_redirect_uri = app.config.get('GMAIL_REDIRECT_URI')

    if not gmail_client_id or not gmail_client_secret or not gmail_scopes or not gmail_redirect_uri:
        app.logger.error("Missing Gmail OAuth credentials in configuration")
        return
    else:
        app.logger.info("Registering Gmail OAuth client")
        app.logger.debug(f"Using Gmail client ID: {gmail_client_id[:5]}...")

        oauth.register(
            name='gmail',
            client_id=gmail_client_id,
            client_secret=gmail_client_secret,
            redirect_uri=gmail_redirect_uri,
            access_token_url='https://oauth2.googleapis.com/token',
            authorize_url='https://accounts.google.com/o/oauth2/auth',
            api_base_url='https://www.googleapis.com/',
            client_kwargs={
                'scope': gmail_scopes.split(),
                'token_endpoint_auth_method': 'client_secret_post'
            }
        )
        app.logger.info("Gmail OAuth client registered successfully")


def hubspot_oauth_client_register(app: Flask):
    client_id = app.config.get('HUBSPOT_CLIENT_ID')
    client_secret = app.config.get('HUBSPOT_CLIENT_SECRET')

    if not client_id or not client_secret:
        app.logger.error("Missing HubSpot OAuth credentials in configuration")
        return

    app.logger.info("Registering HubSpot OAuth client")
    app.logger.debug(f"Using client ID: {client_id[:5]}...")

    oauth.register(
        name='hubspot',
        client_id=client_id,
        client_secret=client_secret,
        access_token_url='https://api.hubapi.com/oauth/v1/token',
        authorize_url='https://app.hubspot.com/oauth/authorize',
        api_base_url='https://api.hubapi.com/',  # Updated base URL
        client_kwargs={
            'scope': 'crm.objects.contacts.read crm.objects.contacts.write crm.objects.deals.read crm.objects.deals.write oauth',
            'token_endpoint_auth_method': 'client_secret_post'
        }
    )
    app.logger.info("HubSpot OAuth client registered successfully")
    
from .fireflies import routes as fireflies_routes
from .hubspot import routes as hubspot_routes
from .gmail import routes as gmail_routes