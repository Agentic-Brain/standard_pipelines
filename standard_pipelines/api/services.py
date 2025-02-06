from abc import ABCMeta, abstractmethod

from standard_pipelines.data_flow.exceptions import APIError, RetriableAPIError

from flask import current_app
from requests.auth import AuthBase
from enum import Enum
from functools import cached_property
import requests
from typing import Optional
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
    def api_url(self, api_context: Optional[dict] = None) -> str:
        pass

    def https_parameters(self, api_context: Optional[dict] = None) -> Optional[dict]:
        debug_msg = (
            f'https_parameters not implemented for {self.__class__.__name__}, '
            'defaulting to None'
        )
        current_app.logger.debug(debug_msg)
        return None

    def https_headers(self, api_context: Optional[dict] = None) -> Optional[dict]:
        debug_msg = (
            f'https_headers not implemented for {self.__class__.__name__}, '
            'defaulting to None'
        )
        current_app.logger.debug(debug_msg)
        return None

    def https_payload(self, api_context: Optional[dict] = None) -> Optional[dict]:
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
        error_msg = f"{response}, {response.text}"
        if status_code >= 500 or status_code == 429:
            raise RetriableAPIError(error_msg)
        if status_code == 401:
            raise APIError(f"Unauthorized: {error_msg}")
        if status_code == 403:
            raise APIError(f"Forbidden: {error_msg}")
        if status_code == 404:
            raise APIError(f"Not Found: {error_msg}")
        if status_code >= 400:
            raise APIError(f"Client Error: {error_msg}")

    @backoff.on_exception(
        backoff.expo,
        (
            RetriableAPIError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ),
        max_tries=5,
    )
    def get_response(self, api_context: Optional[dict] = None):
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