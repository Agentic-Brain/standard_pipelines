from sqlalchemy import Text, Integer, String, ForeignKey, UUID
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from standard_pipelines.api.google.models import GoogleCredentials
from standard_pipelines.api.google.gmail_services import GmailAPIManager
from standard_pipelines.api.openai.services import OpenAIAPIManager
from standard_pipelines.database.models import ScheduledMixin
from ..models import DataFlowConfiguration
from standard_pipelines.api.openai.models import OpenAICredentials
from flask import current_app
from standard_pipelines.extensions import db
from .prompts import FOLLOWUP_PROMPT, EMAIL_BODY_PROMPT

class GmailIntervalFollowupConfiguration(DataFlowConfiguration):
    __tablename__ = 'gmail_interval_followup_configuration'

    email_interval_days: Mapped[int] = mapped_column(Integer, server_default="10080")
    email_retries: Mapped[int] = mapped_column(Integer, server_default="5")
    email_body_prompt: Mapped[str] = mapped_column(Text, default=EMAIL_BODY_PROMPT)
    followup_body_prompt: Mapped[str] = mapped_column(Text, default=FOLLOWUP_PROMPT)
    subject_line_template: Mapped[str] = mapped_column(Text, default="Follow up and next steps")
    internal_domain: Mapped[str] = mapped_column(String(255))
    
class GmailIntervalFollowupSchedule(ScheduledMixin):
    __tablename__ = 'gmail_interval_followup_schedule'
    __abstract__ = False
    configuration_id: Mapped[UUID] = mapped_column(ForeignKey('gmail_interval_followup_configuration.id'))
    thread_id: Mapped[str] = mapped_column(String(255))
    gmail_credentials_id: Mapped[UUID] = mapped_column(ForeignKey('google_credential.id'))
    original_transcript: Mapped[str] = mapped_column(Text)

    configuration: Mapped[GmailIntervalFollowupConfiguration] = relationship()
    gmail_credentials: Mapped['GoogleCredentials'] = relationship()
    
    def _get_openai_credentials(self):
        return OpenAICredentials.query.filter(
            OpenAICredentials.client_id == self.configuration.client_id
        ).first()
    
    def _get_api_managers(self):
        openai_credentials = self._get_openai_credentials()
        if openai_credentials is None:
            raise ValueError("OpenAI credentials not found for this client")
        
        google_api_config = {'refresh_token': self.gmail_credentials.refresh_token}
        if google_api_config is None:
            raise ValueError("Google API credentials not found for this client")
        
        openai_api_config = {'api_key': openai_credentials.openai_api_key}
        
        openai_api_manager = OpenAIAPIManager(api_config=openai_api_config)
        gmail_client = GmailAPIManager(api_config=google_api_config)
   
        return openai_api_manager, gmail_client
        
    def run_job(self) -> bool:
        current_app.logger.debug(f"Running job for {self}")
        config = GmailIntervalFollowupConfiguration.query.get(self.configuration_id)
        if config is None:
            raise ValueError("Configuration not found")
        
        openai_api_manager, gmail_client = self._get_api_managers()  
        followup_prompt = self.configuration.followup_body_prompt.format(original_transcript=self.original_transcript)
        followup_body = openai_api_manager.chat(followup_prompt, model="gpt-4").choices[0].message.content
        to_addresses = gmail_client.get_to_addresses_from_thread(self.thread_id)
        current_app.logger.debug(f"Creating draft for thread {self.thread_id}")
        gmail_client.create_draft(to_addresses, config.subject_line_template, followup_body, self.thread_id)
        return True
    
    def poll(self) -> bool:
        current_app.logger.debug(f"Polling for {self}")
        openai_api_manager, gmail_client = self._get_api_managers()
        try:
            if gmail_client.has_recipient_responded(self.thread_id, self.gmail_credentials.user_email):
                current_app.logger.debug(f"Recipient responded to {self.thread_id}, stopping followup")
                self.stop_schedule()
                db.session.commit()
                return True
        # TODO: fin more specific exception
        except Exception as e:
            current_app.logger.error(f"Error polling for {self}: {e}")
            return False
        return False
    