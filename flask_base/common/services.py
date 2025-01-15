import contextlib
import io
from flask import current_app
from .models import Notification
from flask_base.extensions import db
from abc import ABCMeta, abstractmethod
import typing as t
import tempfile
import json
import os

from singer_sdk import Tap, Target

@contextlib.contextmanager
def temp_json_file(data: dict):
    """Context manager that creates a temporary JSON file and cleans it up after use."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as temp_file:
        json.dump(data, temp_file)
        temp_file.flush()
        yield temp_file.name

class BaseDataFlowService(metaclass=ABCMeta):
    def __init__(self, tap_config: dict, target_config: dict, tap_catalog: os.PathLike):
        self.tap_config = tap_config
        self.target_config = target_config
        self.tap_catalog = tap_catalog

    def run(self, data: t.Any = None, context: t.Optional[dict] = None):
        self.transform(data, context)
        try:
            self.load(context)
        except Exception as e:
            self.handle_load_failure(e)
        self.notify(context)

    def handle_load_failure(self, exception: Exception):
        current_app.logger.error(f'load failed: {exception}')

    def add_notification(self, notification: dict):
        current_app.logger.info(f'Adding notification: {notification}')
        db.session.add(Notification(**notification))
        db.session.commit()
    
    @abstractmethod
    def transform(self, data: t.Any = None, context: t.Optional[dict] = None):
        pass

    @abstractmethod
    def load(self, context: t.Optional[dict] = None):
        pass

    @property
    @abstractmethod
    def _apprise_uri(self):
        pass

    def tap_2_target(self, tap: Tap, target: Target):
        with (
            temp_json_file(self.tap_config) as tap_config_path,
            temp_json_file(self.target_config) as target_config_path
        ):
            current_app.logger.info(f'tap_config_path: {tap_config_path}')
            current_app.logger.info(f'target_config_path: {target_config_path}')
            current_app.logger.info(f'tap_catalog: {self.tap_catalog}')
            tap_output_buffer = io.StringIO()
            with contextlib.redirect_stdout(tap_output_buffer):
                tap.invoke(
                    config=(tap_config_path,),
                    catalog=self.tap_catalog
                )

            tap_output_buffer.seek(0)
            target.invoke(
                config=(target_config_path,),
                file_input=tap_output_buffer
            )

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
            current_app.logger.info(f'Sending notification for notification record: {notification}')
            current_app.logger.info(f'Apprise URI: {self._apprise_uri}')
            notification.sent = apobj.notify(
                body=notification.body,
                title=notification.title
            )
            if notification.sent is False:
                current_app.logger.error(f'Failed to send notification for notification record: {notification}')
            db.session.commit()
