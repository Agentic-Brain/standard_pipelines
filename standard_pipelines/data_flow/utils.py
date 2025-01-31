from __future__ import annotations

import contextlib
from enum import Enum
from functools import cached_property
import io
import uuid
from flask import current_app
import requests
from .models import Client, Notification
from .exceptions import APIError, RetriableAPIError
from standard_pipelines.extensions import db
from abc import ABCMeta, abstractmethod
import typing as t
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectWithAssociations
from hubspot.crm.associations import BatchInputPublicObjectId
from hubspot.crm.contacts import SimplePublicObjectInput as ContactInput
from hubspot.crm.deals import SimplePublicObjectInput as DealInput
from hubspot.files import ApiException
from requests.auth import AuthBase
import backoff
from collections import defaultdict
from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion
from openai import OpenAIError
from .models import DataFlowConfiguration
import inspect

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
        debug_msg = (
            f'https_parameters not implemented for {self.__class__.__name__}, '
            'defaulting to None'
        )
        current_app.logger.debug(debug_msg)
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
        status_code = response.status_code
        if status_code >= 500 or status_code == 429:
            error_msg = f"{response}, {response.text}"
            raise RetriableAPIError(error_msg)
        if status_code >= 400:
            error_msg = f"{response}, {response.text}"
            raise APIError(error_msg)

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


class DataFlowRegistryMeta(ABCMeta):

    DATA_FLOW_REGISTRY: dict[uuid.UUID, type[BaseDataFlow]] = {}

    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)

        if inspect.isabstract(new_cls):
            return new_cls
        
        if not hasattr(new_cls, 'data_flow_id'):
            raise ValueError(f"Class {name} must implement data_flow_id to be registered.")

        data_flow_id = new_cls.data_flow_id()
        if data_flow_id in cls.DATA_FLOW_REGISTRY:
            raise ValueError(f"data_flow_id is already registered as {cls.DATA_FLOW_REGISTRY[data_flow_id].__name__}: {data_flow_id}")
        cls.DATA_FLOW_REGISTRY[data_flow_id] = new_cls

        return new_cls

    @classmethod
    def data_flow_class(cls, dataflow_id: uuid.UUID) -> type[BaseDataFlow]:
        if dataflow_id not in cls.DATA_FLOW_REGISTRY:
            raise ValueError(f"No dataflow class found for {dataflow_id}")
        return cls.DATA_FLOW_REGISTRY[dataflow_id]


DataFlowConfigurationType = t.TypeVar("DataFlowConfigurationType", bound=DataFlowConfiguration)

class BaseDataFlow(t.Generic[DataFlowConfigurationType], metaclass=DataFlowRegistryMeta):

    def __init__(self, client_id: str) -> None:
        self.client_id = client_id

    @classmethod
    @abstractmethod
    def data_flow_id(cls) -> uuid.UUID:
        """ID of the data flow in the database."""

    @cached_property
    def _configuration_class(self) -> type[DataFlowConfigurationType]:
        from typing import get_args
        return get_args(self.__class__.__orig_bases__[0])[0]

    @property
    def configuration(self) -> DataFlowConfigurationType:
        """Return the configuration with the matching client ID and data flow ID."""
        return self._configuration_class.query.filter(
            self._configuration_class.client_id == self.client_id,
            self._configuration_class.registry_id == self.data_flow_id()
        ).first()

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
        """Run each stage of ETL in sequence, stopping if any stage fails."""

        success = True

        try:
            input_data: dict = self.extract(context)
        except Exception as e:
            self.handle_extract_failure(e)
            success = False

        if success:
            try:
                output_data: dict = self.transform(input_data, context)
            except Exception as e:
                self.handle_transform_failure(e)
                success = False

        if success:
            try:
                self.load(output_data, context)
            except Exception as e:
                self.handle_load_failure(e)
                success = False

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

    def verify_config(self, config_name: str):
        if config_name not in current_app.config:
            current_app.logger.error(f'{config_name} not found in application config')
            return False
        return True

    def notify(self, context: t.Optional[dict] = None):
        import apprise

        unsent_notifications = Notification.query.filter_by(sent=False).all()
        notifications_by_uri = defaultdict(list)

        for notification in unsent_notifications:
            notifications_by_uri[notification.uri].append(notification)

        for uri, notifications in notifications_by_uri.items():
            apobj = apprise.Apprise()
            apobj.add(uri)
            for notification in notifications:
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
        return self.api_client.oauth.tokens_api.create(
            grant_type="refresh_token",
            client_id=self.api_config["client_id"],
            client_secret=self.api_config["client_secret"],
            refresh_token=self.api_config["refresh_token"],
        ).access_token

    def all_contacts(self) -> list[dict]:
        return [contact.to_dict() for contact in self.api_client.crm.contacts.get_all()]

    def contact_by_contact_id(self, contact_id: str, properties: list[str] = []) -> dict:
        contact: SimplePublicObjectWithAssociations = self.api_client.crm.contacts.basic_api.get_by_id(contact_id, properties=properties)
        return contact.to_dict()
    
    def deal_by_deal_id(self, deal_id: str, properties: list[str] = []) -> dict:
        deal: SimplePublicObjectWithAssociations = self.api_client.crm.deals.basic_api.get_by_id(deal_id, properties=properties)
        return deal.to_dict()
    
    def contact_by_name_or_email(self, name: t.Optional[str] = None, email: t.Optional[str] = None) -> dict:
        all_contacts = self.all_contacts()
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

    def deal_by_contact_id(self, contact_id: str) -> dict:
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
        deal_association_to = deal_associations[0]["to"]
        contact_to_deal_associations = []
        for deal_association in deal_association_to:
            if deal_association["type"] == "contact_to_deal":
                contact_to_deal_associations.append(deal_association)
        if len(contact_to_deal_associations) > 1:
            error_msg = f"Multiple deals found for contact {contact_id}."
            raise APIError(error_msg)
        if len(contact_to_deal_associations) == 0:
            error_msg = f"No deal found for contact {contact_id}."
            raise APIError(error_msg)
        deal_id = contact_to_deal_associations[0]["id"]
        return self.deal_by_deal_id(deal_id)

    def create_contact(self, email: str | None = None, first_name: str | None = None, last_name: str | None = None) -> dict:
        """
        Creates a new contact in HubSpot with the given email/first/last name.
        Returns the contact as a dictionary.
        """
        props = {}
        if email:
            props["email"] = email
        if first_name:
            props["firstname"] = first_name
        if last_name:
            props["lastname"] = last_name

        contact_input = ContactInput(properties=props)

        try:
            new_contact = self.api_client.crm.contacts.basic_api.create(contact_input)
        except ApiException as e:
            print(f"Error creating contact: {e}")
            raise

        return new_contact.to_dict()

    def create_deal(self, deal_name: str, stage_id: str, contact_id: t.Optional[str] = None) -> dict:
        """
        Creates a new deal in HubSpot, optionally associating it with the provided contact_id.
        
        :param deal_name: The name for the new deal
        :param contact_id: Optional HubSpot contact ID to associate with the deal
        :return: Dictionary containing the newly created deal
        """
        # Prepare the deal input with a valid stage ID
        deal_input = DealInput(
            properties={
                "dealname": deal_name,
                "pipeline": "default",
                "dealstage": stage_id
            }
        )

        try:
            # Create the deal
            new_deal = self.api_client.crm.deals.basic_api.create(deal_input)
            deal_dict = new_deal.to_dict()
            deal_id = deal_dict.get("id")

            if not deal_id:
                raise APIError("Failed to retrieve 'id' from newly created deal.")

            # If we have a contact_id, create the association
            if contact_id:
                batch_input = BatchInputPublicObjectId(
                    inputs=[
                        {
                            "from": {"id": contact_id},
                            "to": {"id": deal_id},
                            "type": "contact_to_deal"
                        }
                    ]
                )

                self.api_client.crm.associations.batch_api.create(
                    "contacts",
                    "deals",
                    batch_input
                )

            return deal_dict

        except ApiException as e:
            print(f"Error creating or associating deal: {e}")
            raise

    def create_meeting(self, meeting_object: dict) -> None:
        self.api_client.crm.objects.meetings.basic_api.create(meeting_object)
    
    def create_note(self, note_object: dict) -> None:
        self.api_client.crm.objects.notes.basic_api.create(note_object)


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
                id
                dateString
                privacy
                speakers {
                    id
                    name
                }
                sentences {
                    index
                    speaker_name
                    speaker_id
                    text
                    raw_text
                    start_time
                    end_time
                }
                title
                host_email
                organizer_email
                calendar_id
                date
                transcript_url
                duration
                meeting_attendees {
                    displayName
                    email
                    phoneNumber
                    name
                    location
                }
                cal_id
                calendar_type
                meeting_link
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

    def transcript(self, transcript_id: str) -> tuple[str, list[str], list[str]]:
        """
        Returns a tuple of a prettified transcript suitable for input into an
        AI prompt, a list of emails present in the transcript, and a list of
        names present in the transcript.
        """
        transcript_object = self.get_response({"transcript_id": transcript_id}).json()
        pretty_transcript = self._pretty_transcript_from_transcript_object(transcript_object)
        emails = self._emails_from_transcript_object(transcript_object)
        names = self._names_from_transcript_object(transcript_object)
        return pretty_transcript, emails, names

    def _emails_from_transcript_object(self, transcript: dict) -> list[str]:
        transcript_data = transcript.get("data", {}).get("transcript", {})
        meeting_attendees = transcript_data.get("meeting_attendees")
        return meeting_attendees if meeting_attendees else []

    def _names_from_transcript_object(self, transcript: dict) -> list[str]:
        transcript_data = transcript.get("data", {}).get("transcript", {})
        try:
            return [speaker.get("name", "") for speaker in transcript_data.get("speakers", [])]
        except Exception as e:
            current_app.logger.error(f"Error getting names from transcript object: {e}")
            return ["Unknown Speaker"]

    def _pretty_transcript_from_transcript_object(self, transcript: dict) -> str:

        if "errors" in transcript:
            warning_msg = f"GraphQL Errors: {transcript['errors']}"
            current_app.logger.warning(warning_msg)
        
        transcript_data = transcript.get("data", {}).get("transcript", {})
        if not transcript_data:
            warning_msg = "No transcript data found."
            current_app.logger.warning(warning_msg)
        sentences = transcript_data.get('sentences', [])
        if not sentences:
            warning_msg = "No sentences found."
            current_app.logger.warning(warning_msg)

        formatted_lines = []
        for sentence in sentences:
            minutes = int(sentence.get("start_time", 0)) // 60
            seconds = int(sentence.get("start_time", 0)) % 60
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            speaker = sentence.get("speaker_name", "Unknown Speaker")
            text = sentence.get("raw_text", "")
            formatted_line = f"{timestamp} {speaker}: {text}"
            formatted_lines.append(formatted_line)

        return "\n".join(formatted_lines)


class OpenAIAPIManager(BaseAPIManager, metaclass=ABCMeta):

    def __init__(self, api_config: dict) -> None:
        super().__init__(api_config)
        self.api_client = OpenAI(api_key=self.api_config["api_key"])

    @property
    def required_config(self) -> list[str]:
        return ["api_key"]
    
    def chat(self, prompt: str, model: str) -> ChatCompletion:
        if not prompt or not model:
            raise ValueError("Prompt and model are required.")
        try:
            return self.api_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
        except OpenAIError as e:
            error_msg = f"Error during OpenAI API call."
            raise APIError(error_msg) from e


