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

class GmailIntervalFollowupConfiguration(DataFlowConfiguration):
    __tablename__ = 'gmail_interval_followup_configuration'

    email_interval_days: Mapped[int] = mapped_column(Integer, default=7)
    email_retries: Mapped[int] = mapped_column(Integer, default=3)
    email_body_prompt: Mapped[str] = mapped_column(Text)
    followup_body_prompt: Mapped[str] = mapped_column(Text)
    subject_line_template: Mapped[str] = mapped_column(Text)
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
    
    def run_job(self) -> bool:
        current_app.logger.debug(f"Running job for {self}")
        config = GmailIntervalFollowupConfiguration.query.get(self.configuration_id)
        if config is None:
            raise ValueError("Configuration not found")
            
        openai_credentials = self._get_openai_credentials()
        if openai_credentials is None:
            raise ValueError("OpenAI credentials not found for this client")
        
        current_app.logger.debug(f"Loading credentials for {self.gmail_credentials}")
        google_api_config = {'refresh_token': self.gmail_credentials.refresh_token}
        
        openai_api_config = {'api_key': openai_credentials.openai_api_key}
        openai_api_manager = OpenAIAPIManager(api_config=openai_api_config)
        
        followup_prompt = self.configuration.followup_body_prompt.format(transcript=self.original_transcript)
        followup_body = openai_api_manager.chat(followup_prompt, model="gpt-4")
        gmail_client = GmailAPIManager(api_config=google_api_config)
        to_addresses = gmail_client.get_to_addresses_from_thread(self.thread_id)
        current_app.logger.debug(f"Creating draft for {self.thread_id} with subject {config.subject_line_template} and body {config.email_body_prompt}")
        gmail_client.create_draft(to_addresses, config.subject_line_template, config.email_body_prompt, self.thread_id)
        return True
