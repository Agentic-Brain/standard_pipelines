from flask import Blueprint, Flask
import requests

from standard_pipelines.extensions import oauth

api = Blueprint('api', __name__, url_prefix='/api')

def init_app(app: Flask):
    app.logger.debug(f'Initializing blueprint {__name__}')
    
    # Initialize the new OAuth system
    try:
        from standard_pipelines.api.oauth_init import init_oauth_system
        init_oauth_system(app)
    except Exception as e:
        app.logger.warning(f"Could not initialize OAuth system: {e}")
    
    # Keep old OAuth registration for backward compatibility - only for services not yet migrated
    # hubspot_oauth_client_register(app)  # Commented out - HubSpot uses new OAuth system



    # Add any API-specific initialization here
    # For example, registering error handlers, before_request handlers, etc.
    
# def google_oauth_client_register(app: Flask):
#     # TODO: Clean this up a little using dict/set checking method
#     google_client_id = app.config.get('GOOGLE_CLIENT_ID')
#     google_client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
#     google_scopes = app.config.get('GOOGLE_SCOPES')
#     google_redirect_uri = app.config.get('GOOGLE_REDIRECT_URI')

#     if not google_client_id or not google_client_secret or not google_scopes or not google_redirect_uri:
#         app.logger.error("Missing Google OAuth credentials in configuration")
#         return
#     else:
#         app.logger.info("Registering Google OAuth client")
#         app.logger.debug(f"Using Google client ID: {google_client_id[:5]}...")

#         oauth.register(
#             name='google',
#             client_id=google_client_id,
#             client_secret=google_client_secret,
#             redirect_uri=google_redirect_uri,
#             access_token_url='https://oauth2.googleapis.com/token',
#             authorize_url='https://accounts.google.com/o/oauth2/auth',
#             api_base_url='https://www.googleapis.com/',
#             client_kwargs={
#                 'scope': google_scopes.split(),
#                 'token_endpoint_auth_method': 'client_secret_post'
#             }
#         )
#         app.logger.info("Google OAuth client registered successfully")


# def hubspot_oauth_client_register(app: Flask):
#     client_id = app.config.get('HUBSPOT_CLIENT_ID')
#     client_secret = app.config.get('HUBSPOT_CLIENT_SECRET')

#     if not client_id or not client_secret:
#         app.logger.error("Missing HubSpot OAuth credentials in configuration")
#         return

#     app.logger.info("Registering HubSpot OAuth client")
#     app.logger.debug(f"Using client ID: {client_id[:5]}...")

#     oauth.register(
#         name='hubspot',
#         client_id=client_id,
#         client_secret=client_secret,
#         access_token_url='https://api.hubapi.com/oauth/v1/token',
#         authorize_url='https://app.hubspot.com/oauth/authorize',
#         api_base_url='https://api.hubapi.com/',  # Updated base URL
#         client_kwargs={
#             'scope': 'crm.objects.contacts.read crm.objects.contacts.write crm.objects.deals.read crm.objects.deals.write crm.schemas.deals.read crm.schemas.deals.write oauth crm.objects.users.read crm.objects.users.write',
#             'token_endpoint_auth_method': 'client_secret_post'
#         }
#     )
#     app.logger.info("HubSpot OAuth client registered successfully")

# def zoho_oauth_client_register(app: Flask):
#     client_id = app.config.get('ZOHO_CLIENT_ID')
#     client_secret = app.config.get('ZOHO_CLIENT_SECRET')

#     if not client_id or not client_secret:
#         app.logger.error("Missing Zoho OAuth credentials in configuration")
#         return

#     app.logger.info("Registering Zoho OAuth client")
#     app.logger.debug(f"Using client ID: {client_id[:5]}...")

#     oauth.register(
#         name='zoho',
#         client_id=client_id,
#         client_secret=client_secret,
#         access_token_url='https://accounts.zoho.com/oauth/v2/token',
#         authorize_url='https://accounts.zoho.com/oauth/v2/auth',
#         api_base_url='https://www.zohoapis.com/',  # Updated base URL
#         client_kwargs={
#             'scope': 'ZohoCRM.users.ALL ZohoCRM.settings.ALL ZohoCRM.modules.ALL ZohoSearch.securesearch.READ ZohoCRM.org.ALL',
#             'token_endpoint_auth_method': 'client_secret_post'
#         }
#     )
#     app.logger.info("Zoho OAuth client registered successfully")

def load_oauth():
    ENDPOINT = 'n8n.agentic-internal.com/api/v1/credentials'
    json = {
        'name': 'test',
        "type": 'goo'
    }
    requests.post()

from .fireflies import routes as fireflies_routes
from .hubspot import routes as hubspot_routes
from .zoho import routes as zoho_routes
from .google import routes as google_routes
from .sharpspring import routes as sharpspring_routes
from .dialpad import routes as dialpad_routes
from .openai import routes as openai_routes
from .notion import routes as notion_routes