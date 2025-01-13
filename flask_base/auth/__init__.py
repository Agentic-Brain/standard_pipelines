from flask import Blueprint, Flask, current_app
# Cryptography
from cryptography.fernet import Fernet
# Flask Security
from flask_security.mail_util import MailUtil
from flask_security.datastore import SQLAlchemyUserDatastore
from flask_security.forms import RegisterForm, LoginForm, ResetPasswordForm
# Application
from flask_base.extensions import db, security, mail
import requests

auth = Blueprint('auth', __name__)


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
    from flask_base.auth.models import Role, User

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

# from . import routes