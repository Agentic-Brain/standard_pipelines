from __future__ import annotations

import contextlib
from functools import cached_property
import json
import uuid
from flask import current_app

from .models import DataFlow, Notification
from standard_pipelines.extensions import db
from abc import ABCMeta, abstractmethod
import typing as t
from collections import defaultdict
from .models import DataFlowConfiguration
import inspect
import sentry_sdk

class DataFlowRegistryMeta(ABCMeta):

    DATA_FLOW_REGISTRY: dict[str, type[BaseDataFlow]] = {}

    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)

        if inspect.isabstract(new_cls):
            return new_cls
        
        if not hasattr(new_cls, 'data_flow_name'):
            raise ValueError(f"Class {name} must implement data_flow_name to be registered.")

        data_flow_name = new_cls.data_flow_name()
        if data_flow_name in cls.DATA_FLOW_REGISTRY:
            raise ValueError(f"data_flow_name is already registered as {cls.DATA_FLOW_REGISTRY[data_flow_name].__name__}: {data_flow_name}")
        cls.DATA_FLOW_REGISTRY[data_flow_name] = new_cls

        return new_cls

    @classmethod
    def data_flow_class(cls, dataflow_name: str) -> type[BaseDataFlow]:
        for df_name in cls.DATA_FLOW_REGISTRY:
            current_app.logger.info(f"DATA_FLOW_REGISTRY: {df_name}")

        if dataflow_name not in cls.DATA_FLOW_REGISTRY:
            raise ValueError(f"No dataflow class found for {dataflow_name}")
        return cls.DATA_FLOW_REGISTRY[dataflow_name]


DataFlowConfigurationType = t.TypeVar("DataFlowConfigurationType", bound=DataFlowConfiguration)

class BaseDataFlow(t.Generic[DataFlowConfigurationType], metaclass=DataFlowRegistryMeta):

    def __init__(self, client_id: str) -> None:
        self.client_id = client_id

    @classmethod
    def data_flow_id(cls) -> uuid.UUID:
        """ID of the data flow in the database."""
        return DataFlow.query.filter_by(name=cls.data_flow_name()).first().id

    @classmethod
    @abstractmethod
    def data_flow_name(cls) -> str:
        """
        Name of the data flow in the database. Must have a matching entry in
        `flows.txt`.
        """

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
        current_app.logger.exception(f'extract failed: {exception}')
        sentry_sdk.capture_exception(exception)

    def handle_transform_failure(self, exception: Exception):
        current_app.logger.exception(f'transform failed: {exception}')
        sentry_sdk.capture_exception(exception)

    def handle_load_failure(self, exception: Exception):
        current_app.logger.exception(f'load failed: {exception}')
        sentry_sdk.capture_exception(exception)

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




