from flask import Blueprint, Flask, current_app
# Cryptography
from cryptography.fernet import Fernet
from typing import Optional
# Flask Security
from flask_security.mail_util import MailUtil
from flask_security.datastore import SQLAlchemyUserDatastore
from flask_security.forms import RegisterForm, LoginForm, ResetPasswordForm
from flask_security.utils import hash_password
# Application
from standard_pipelines.extensions import db, security, mail
from bitwarden_sdk import BitwardenClient, client_settings_from_dict, DeviceType, ResponseForProjectResponse
import requests
import click
from standard_pipelines.data_flow.models import Client
from standard_pipelines.extensions import oauth

auth = Blueprint('auth', __name__)
bitwarden_client: Optional[BitwardenClient] = None
bitwarden_project: Optional[ResponseForProjectResponse] = None

class MailgunMailUtil(MailUtil):
    def send_mail(self, template, subject, recipient, sender, body, html, **kwargs):
        send_mailgun_email(
            subject=subject,
            sender=sender,
            recipients=[recipient],
            body=body,
            html=html,
        )

def send_mailgun_email(**kwargs):
    try:
        response = requests.post(
            f"https://api.mailgun.net/v3/{current_app.config['MAILGUN_SEND_DOMAIN']}/messages",
            auth=("api", current_app.config['MAILGUN_API_KEY']),
            data={
                "from": kwargs['sender'],
                "to": kwargs['recipients'],
                "subject": kwargs['subject'],
                "text": kwargs['body'],
                "html": kwargs['html']
            }
        )
        response.raise_for_status()
        print(f"Email sent successfully via Mailgun to {kwargs['recipients']}")
    except requests.RequestException as e:
        print(f"Failed to send email via Mailgun: {str(e)}")

def init_app(app: Flask):
    app.logger.debug(f'Initalizing blueprint {__name__}')
    mail.init_app(app)
    oauth.init_app(app)
    oauth_client_register(app)
    # Importing here prevents a circular import
    from standard_pipelines.auth.models import Role, User

    app.logger.debug(f'Creating user_datastore')
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    
    app.logger.debug('Initializing security object')
    security.init_app(app, 
                    user_datastore,
                    register_form=RegisterForm,
                    login_form=LoginForm,
                    reset_password_form=ResetPasswordForm,
                    mail_util_cls=MailgunMailUtil)
    
    app.user_datastore = user_datastore # type: ignore
    app.logger.debug('Creating cipher from encryption key')
    app.extensions['cipher'] = Fernet(app.config['ENCRYPTION_KEY']) # type: ignore
    app.extensions['security'] = security
    
    app.logger.debug('Creating bitwarden client')
    bitwarden_client = BitwardenClient(
        client_settings_from_dict(
            {
                "device_type": DeviceType.SDK,
                "userAgent": "Python"
            }
        )
    )
    
    bitwarden_client.auth().login_access_token(app.config['BITWARDEN_ACCESS_TOKEN'], app.config['BITWARDEN_STATE_FILE_PATH'])
    app.extensions['bitwarden_client'] = bitwarden_client
    
    app.cli.add_command(create_default_admin)

@click.command('create-default-admin')
def create_default_admin():
    """Create default internal client and admin user if they don't exist."""
    from standard_pipelines.auth.models import User, Role
    from standard_pipelines.data_flow.models import Client
    
    # 1. Create default internal client if it doesn't exist.
    client_name = current_app.config['DEFAULT_CLIENT_NAME']
    default_client = Client.query.filter_by(name=client_name).first()
    if not default_client:
        default_client = Client(
            name=client_name,
            description='Default internal client',
            bitwarden_encryption_key_id=current_app.config['DEFAULT_CLIENT_BITWARDEN_KEY_ID']
        )
        db.session.add(default_client)
        current_app.logger.info(f'Created default client: {client_name}')
        db.session.flush()  # So that default_client has an ID before assigning it to a user

    # 2. Check if the admin user already exists.
    admin_email = current_app.config['DEFAULT_ADMIN_ACCOUNT']
    existing_admin = current_app.user_datastore.find_user(email=admin_email)
    if existing_admin:
        current_app.logger.info(f'Admin user {admin_email} already exists')
        return

    # 3. Ensure the "admin" role exists (create if not).
    admin_role_name = 'admin'
    admin_role = current_app.user_datastore.find_role(admin_role_name)
    if not admin_role:
        admin_role = current_app.user_datastore.create_role(
            name=admin_role_name,
            description='Administrator'
        )
        current_app.logger.info(f'Created {admin_role_name} role')

    # 4. Create the admin user using Flask-Security datastore.
    admin_user = current_app.user_datastore.create_user(
        email=admin_email,
        password=hash_password(current_app.config['DEFAULT_ADMIN_PASSWORD']),
        roles=[admin_role],
        active=True,
        confirmed_at=db.func.now(),  # or datetime.utcnow() if you prefer
        client=default_client       # Link to the client foreign key
    )

    # 5. Commit the changes to the database.
    current_app.user_datastore.commit()
    current_app.logger.info(f'Created admin user: {admin_email} linked to client: {client_name}')

def oauth_client_register(app: Flask):
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

from . import routes