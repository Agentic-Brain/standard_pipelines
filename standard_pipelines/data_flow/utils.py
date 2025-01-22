from __future__ import annotations

import contextlib
from enum import Enum
from functools import cached_property
import io
from flask import current_app
import requests
from .models import Client, Notification
from .exceptions import APIError, RetriableAPIError
from standard_pipelines.extensions import db
from abc import ABCMeta, abstractmethod
import typing as t
import tempfile
import json
import os
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectWithAssociations
from hubspot.crm.associations import BatchInputPublicObjectId
from requests.auth import AuthBase
import backoff

class BaseAPIManager(metaclass=ABCMeta):

    def __init__(self, api_config: dict) -> None:
        self.validate_api_config(api_config)
        self.api_config = api_config

    def validate_api_config(self, api_config: dict) -> None:
        missing_config = set(self.required_config).difference(set(api_config.keys()))
        if missing_config:
            raise ValueError(f"Missing required keys in api_config: {missing_config}")

    @property
    @abstractmethod
    def required_config(self) -> list[str]:
        pass


# TODO: clunky abstraction, works for now and not a priority, but this smells
class BaseManualAPIManager(BaseAPIManager, metaclass=ABCMeta):
    """
    For APIs that do not have an SDK available and require API calls to be
    managed manually.
    """

    class PayloadType(Enum):
        JSON = "json"
        DATA = "data"

    @cached_property
    def _requests_session(self):
        session = requests.Session()
        session.auth = self.authenticator()
        return session

    @property
    def payload_type(self) -> PayloadType:
        return self.PayloadType.JSON

    @property
    def timeout(self) -> int:
        """Measured in seconds"""
        return 300

    @property
    def https_method(self) -> str:
        return "POST"

    @abstractmethod
    def api_url(self, api_context: t.Optional[dict] = None) -> str:
        pass

    def https_parameters(self, api_context: t.Optional[dict] = None) -> t.Optional[dict]:
        # debug_msg = (
        #     f'https_parameters not implemented for {self.__class__.__name__}, '
        #     'defaulting to None'
        # )
        # current_app.logger.debug(debug_msg)
        return None

    def https_headers(self, api_context: t.Optional[dict] = None) -> t.Optional[dict]:
        debug_msg = (
            f'https_headers not implemented for {self.__class__.__name__}, '
            'defaulting to None'
        )
        current_app.logger.debug(debug_msg)
        return None

    def https_payload(self, api_context: t.Optional[dict] = None) -> t.Optional[dict]:
        debug_msg = (
            f'https_payload not implemented for {self.__class__.__name__}, '
            'defaulting to None'
        )
        current_app.logger.debug(debug_msg)
        return None

    def authenticator(self) -> AuthBase:
        debug_msg = (
            f'authenticator not implemented for {self.__class__.__name__}, '
            'defaulting to a callable with no changes to the request'
        )
        current_app.logger.debug(debug_msg)

        class NullAuthenticator(AuthBase):
            def __call__(self, r):
                return r

        return NullAuthenticator()

    def validate_response(self, response: requests.Response):
        breakpoint()
        status_code = response.status_code
        if status_code >= 500 or status_code == 429:
            raise RetriableAPIError(response)
        if status_code >= 400:
            raise APIError(response)

    @backoff.on_exception(
        backoff.expo,
        (
            RetriableAPIError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ),
        max_tries=5,
    )
    def get_response(self, api_context: t.Optional[dict] = None):
        request = requests.Request(
            method=self.https_method,
            url=self.api_url(api_context),
            params=self.https_parameters(api_context),
            headers=self.https_headers(api_context),
            **{self.payload_type.value: self.https_payload(api_context)},
        )
        response = self._requests_session.send(
            request=self._requests_session.prepare_request(request),
            timeout=self.timeout,
        )
        self.validate_response(response)
        return response


class BaseDataFlowService(metaclass=ABCMeta):

    def __init__(self, client_id: str) -> None:
        self.client_id = client_id

    @cached_property
    def bitwarden_api_manager(self) -> BitwardenAPIManager:
        bitwarden_encryption_key_id = Client.query.filter_by(id=self.client_id).first().bitwarden_encryption_key_id
        api_config = {
            "encryption_key_id": bitwarden_encryption_key_id
        }
        return BitwardenAPIManager(api_config)

    @abstractmethod
    def context_from_webhook_data(self, webhook_data: t.Any) -> t.Optional[dict]:
        """
        Returns:
            dict: the webhook data is valid and we should run the data flow
            None: the webhook data is valid but no action needs to be taken
        Raises:
            InvalidWebhookError: the webhook is invalid and something went wrong
        """

    def webhook_run(self, webhook_data: t.Any = None):
        context = self.context_from_webhook_data(webhook_data)
        self.run(context)

    def run(self, context: t.Optional[dict] = None):
        try:
            input_data: dict = self.extract(context)
        except Exception as e:
            self.handle_extract_failure(e)
        try:
            output_data: dict = self.transform(input_data, context)
        except Exception as e:
            self.handle_transform_failure(e)
        try:
            self.load(output_data, context)
        except Exception as e:
            self.handle_load_failure(e)
        self.notify(context)

    def handle_extract_failure(self, exception: Exception):
        current_app.logger.error(f'extract failed: {exception}')

    def handle_transform_failure(self, exception: Exception):
        current_app.logger.error(f'transform failed: {exception}')

    def handle_load_failure(self, exception: Exception):
        current_app.logger.error(f'load failed: {exception}')

    def add_notification(self, notification: dict):
        db.session.add(Notification(**notification))
        db.session.commit()
    
    @abstractmethod
    def extract(self, context: t.Optional[dict] = None) -> dict:
        pass
    
    @abstractmethod
    def transform(self, input_data: t.Optional[dict] = None, context: t.Optional[dict] = None) -> dict:
        pass

    @abstractmethod
    def load(self, output_data: t.Optional[dict] = None, context: t.Optional[dict] = None) -> None:
        pass

    @property
    @abstractmethod
    def _apprise_uri(self):
        pass

    def verify_config(self, config_name: str):
        if config_name not in current_app.config:
            current_app.logger.error(f'{config_name} not found in application config')
            return False
        return True

    def notify(self, context: t.Optional[dict] = None):
        import apprise
        apobj = apprise.Apprise()
        apobj.add(self._apprise_uri)
        for notification in Notification.query.filter_by(sent=False).all():
            notification.sent = apobj.notify(
                body=notification.body,
                title=notification.title
            )
            db.session.commit()


class HubSpotAPIManager(BaseAPIManager, metaclass=ABCMeta):

    def __init__(self, api_config: dict) -> None:
        super().__init__(api_config)
        self.api_client = HubSpot()
        self.api_client.access_token = self.access_token
    
    @property
    def required_config(self) -> list[str]:
        return ["client_id", "client_secret", "refresh_token"]

    @property
    def access_token(self) -> str:
        foo = self.api_client.oauth.tokens_api.create(
            grant_type="refresh_token",
            client_id=self.api_config["client_id"],
            client_secret=self.api_config["client_secret"],
            refresh_token=self.api_config["refresh_token"],
        )
        return foo.access_token

    def get_all_contacts(self) -> list[dict]:
        return [contact.to_dict() for contact in self.api_client.crm.contacts.get_all()]
    
    def get_contact_by_name_or_email(self, name: t.Optional[str] = None, email: t.Optional[str] = None) -> dict:
        all_contacts = self.get_all_contacts()
        matching_contacts = []
        for contact in all_contacts:
            contact_first_name = contact.get("properties", {}).get("firstname", "") 
            contact_last_name = contact.get("properties", {}).get("lastname", "")
            contact_full_name = f"{contact_first_name} {contact_last_name}".strip()
            contact_email = contact.get("properties", {}).get("email", "")
            if (
                name is not None and contact_full_name == name
                or email is not None and contact_email == email
            ):
                matching_contacts.append(contact)
        if len(matching_contacts) > 1: # TODO: better error handling
            error_msg = f"Multiple contacts found for {email} or {name}."
            raise APIError(error_msg)
        if len(matching_contacts) == 0:
            error_msg = f"No contact found for {email} or {name}."
            raise APIError(error_msg)
        return matching_contacts[0]

    def get_deal_by_contact_id(self, contact_id: str) -> dict:
        batch_ids = BatchInputPublicObjectId([{"id": contact_id}])
        deal_associations = self.api_client.crm.associations.batch_api.read(
            from_object_type="contacts",
            to_object_type="deals",
            batch_input_public_object_id=batch_ids,
        ).to_dict()["results"]
        if len(deal_associations) > 1:
            error_msg = f"Multiple deals found for contact {contact_id}."
            raise APIError(error_msg)
        if len(deal_associations) == 0:
            error_msg = f"No deal found for contact {contact_id}."
            raise APIError(error_msg)
        deal_association = deal_associations[0]["to"]
        deal_association_type = deal_association["type"]
        if deal_association_type != "contact_to_deal":
            error_msg = (
                f"Incorrect association type for contact {contact_id}. Should "
                f"be 'contact_to_deal' but got '{deal_association_type}'."
            )
            raise APIError(error_msg)
        deal_id = deal_association["id"]
        return self.get_deal_by_deal_id(deal_id)

    def get_contact_by_contact_id(self, contact_id: str) -> dict:
        contact: SimplePublicObjectWithAssociations = self.api_client.crm.contacts.basic_api.get_by_id(contact_id)
        return contact.to_dict()
    
    def get_deal_by_deal_id(self, deal_id: str) -> dict:
        deal: SimplePublicObjectWithAssociations = self.api_client.crm.deals.basic_api.get_by_id(deal_id)
        return deal.to_dict()

    def log_meeting(self, meeting_object: dict) -> None:
        self.api_client.crm.objects.meetings.basic_api.create(meeting_object)


class FirefliesAPIManager(BaseManualAPIManager, metaclass=ABCMeta):

    class FirefliesAuthenticator(AuthBase):
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

        def __call__(self, r):
            r.headers["Authorization"] = f"Bearer {self.api_key}"
            return r
    
    def authenticator(self) -> AuthBase:
        return self.FirefliesAuthenticator(self.api_config["api_key"])

    @property
    def required_config(self) -> list[str]:
        return ["api_key"]

    def api_url(self, api_context: t.Optional[dict] = None) -> str:
        return "https://api.fireflies.ai/graphql"

    def https_payload(self, api_context: t.Optional[dict] = None) -> t.Optional[dict]:
        query_string = """
            query Transcript($transcriptId: String!) {
                transcript(id: $transcriptId) {
                    title
                    id
                    sentences {
                        index
                        speaker_name
                        start_time
                        raw_text
                    }
                    participants
                    meeting_attendees {
                        email
                        name
                    }
                }
            }
        """
        return {
            "query": query_string,
            "variables": {"transcriptId": api_context["transcript_id"]}
        }
    
    def https_headers(self, api_context: t.Optional[dict] = None) -> t.Optional[dict]:
        return {
            "Content-Type": "application/json",
        }

    def get_transcript(self, transcript_id: str) -> dict:
        response = self.get_response({"transcript_id": transcript_id})
        return response.json()


class BitwardenAPIManager(BaseManualAPIManager, metaclass=ABCMeta):

    @property
    def required_config(self) -> list[str]:
        return ["encryption_key_id"]

    def api_url(self, api_context: t.Optional[dict] = None) -> str:
        return "placeholder"

    def get_secret(self, secret_id: str) -> str:
        return "placeholder"
