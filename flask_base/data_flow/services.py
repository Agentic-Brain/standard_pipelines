import typing as t
import re
import requests
from flask import current_app
from tap_hubspot.tap import TapHubspot
from target_postgres.target import TargetPostgres
from flask_base.common.services import BaseDataFlowService
from .models import Contact
import json
import io
import contextlib

class HubSpotNotificationEmailOnContactUpdate(BaseDataFlowService):

    # TODO: read from database for a specific client
    @classmethod
    def new_instance_from_env(cls) -> 'HubSpotNotificationEmailOnContactUpdate':
        return cls(
            tap_config={
                "client_id": current_app.config['HUBSPOT_CLIENT_ID'],
                "client_secret": current_app.config['HUBSPOT_CLIENT_SECRET'],
                "refresh_token": current_app.config['HUBSPOT_REFRESH_TOKEN']
            },
            target_config={
                "sqlalchemy_url": current_app.config['POSTGRES_SQLALCHEMY_URL']
            },
            tap_catalog=current_app.config['TAP_HUBSPOT_CONTACTS_CATALOG_PATH'],
        ) 

    def transform(self, data: t.Any = None, context: t.Optional[dict] = None):
        for item in data:
            if item['subscriptionType'] == 'contact.propertyChange' and item['propertyName'] == 'email':
                contact_id = item['objectId']
                current_app.logger.info(f'Contact ID: {contact_id}')

                contact = Contact.query.filter_by(hubspot_id=str(contact_id)).first()
                current_app.logger.info(f'Contact Found: {contact}')

                # TODO: use AI to generate the email body
                notification = {
                    'title': "Contact Updated",
                    'body': f"Email updated for contact: {contact.full_name}"
                }
                current_app.logger.info(f'Notification: {notification}')
                self.add_notification(notification)

    def load(self, context: t.Optional[dict] = None):
        """
        Here's where we perform logic to use meltano to load from postgres to
        the target system. Not needed for this service.
        """

    # TODO: lookup based on the specific client
    # TODO: allow multiple recipients per URI
    # TODO: allow multiple URIs per client?
    @property
    def _apprise_uri(self): 

        if not self.verify_config('MAILGUN_API_KEY'):
            return None
        if not self.verify_config('MAILGUN_SEND_DOMAIN'):
            return None
        if not self.verify_config('MAILGUN_SEND_USER'):
            return None
        if not self.verify_config('MAILGUN_RECIPIENT'):
            return None

        user = current_app.config['MAILGUN_SEND_USER']
        domain = current_app.config['MAILGUN_SEND_DOMAIN']
        apikey = current_app.config['MAILGUN_API_KEY']
        emails = [current_app.config['MAILGUN_RECIPIENT']]
        return f'mailgun://{user}@{domain}/{apikey}/{"/".join(emails)}'

    # TODO: there must be a better way to do this. Loading context should not
    # need to be a two-step process.
    def load_context(self):
        self.tap_2_target(TapHubspot, TargetPostgres)
        self._sync_contacts_to_flask()

    def _sync_contacts_to_flask(self):
        from flask import current_app
        from sqlalchemy import text
        from .models import Contact
        from flask_base.extensions import db

        with current_app.app_context():

            Contact.query.delete()
            
            # TODO: use sqlalchemy instead of raw sql
            # TODO: can this be genericized for any data flow service?
            sql = text("""
                SELECT 
                    id,
                    properties,
                    "createdAt" as created_at,
                    "updatedAt" as updated_at,
                    archived,
                    lastmodifieddate
                FROM melty.contacts
                WHERE archived = false
                ORDER BY "createdAt"
            """)
            
            result = db.session.execute(sql)
            
            contacts = []
            for row in result:
                # Parse the JSONB properties column
                props = row.properties or {}
                
                contact = Contact(
                    hubspot_id=row.id,
                    email=props.get('email'),
                    firstname=props.get('firstname'),
                    lastname=props.get('lastname'),
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    last_modified_date=row.lastmodifieddate
                )
                contacts.append(contact)
            
            # Bulk insert all contacts
            db.session.bulk_save_objects(contacts)
            db.session.commit()
