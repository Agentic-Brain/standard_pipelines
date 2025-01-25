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
    
    app.cli.add_command(create_admin)

@click.command('create-admin')
def create_admin():
    """Create default internal client and admin user if they don't exist."""
    from standard_pipelines.auth.models import User, Role
    from standard_pipelines.data_flow.models import Client
    
    # First create default internal client if it doesn't exist
    client_name = current_app.config['DEFAULT_CLIENT_NAME']
    default_client = Client.query.filter_by(name=client_name).first()
    
    if not default_client:
        default_client = Client(
            name=client_name,
            description='Default internal client',
            bitwarden_encryption_key_id=current_app.config['DEFAULT_CLIENT_BITWARDEN_KEY_ID']  # You might want to set this from config
        )
        db.session.add(default_client)
        current_app.logger.info(f'Created default client: {client_name}')
        db.session.flush()  # Flush to get the client ID
    
    # Check if admin user exists
    admin_email = current_app.config['SECURITY_EMAIL']
    existing_admin = User.query.filter_by(email=admin_email).first()
    
    if existing_admin:
        current_app.logger.info(f'Admin user {admin_email} already exists')
        return
    
    # Ensure admin role exists
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(name='admin', description='Administrator')
        db.session.add(admin_role)
        current_app.logger.info('Created admin role')
    
    # Create admin user
    admin_user = User(
        email=admin_email,
        password=hash_password(current_app.config['SECURITY_PASSWORD']),
        roles=[admin_role],
        active=True,
        confirmed_at=db.func.now(),  # Set confirmed_at to current timestamp
        client=default_client  # Link to default client
    )
    
    db.session.add(admin_user)
    db.session.commit()
    current_app.logger.info(f'Created admin user: {admin_email} linked to client: {client_name}')

from . import routes
