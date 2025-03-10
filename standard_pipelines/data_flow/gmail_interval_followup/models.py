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

# TODO: Error handle for unfound thread ID, clogs up sentry right now
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
        current_app.logger.debug(f"Retrieving OpenAI credentials for client_id: {self.configuration.client_id}")
        credentials = OpenAICredentials.query.filter(
            OpenAICredentials.client_id == self.configuration.client_id
        ).first()
        if credentials:
            current_app.logger.debug(f"OpenAI credentials found for client_id: {self.configuration.client_id}")
        else:
            current_app.logger.error(f"OpenAI credentials NOT found for client_id: {self.configuration.client_id}")
        return credentials
    
    def _get_api_managers(self):
        current_app.logger.debug(f"Initializing API managers for job: {self.id}")
        openai_credentials = self._get_openai_credentials()
        if openai_credentials is None:
            current_app.logger.error(f"OpenAI credentials not found for client_id: {self.configuration.client_id}")
            raise ValueError("OpenAI credentials not found for this client")
        
        google_api_config = {'refresh_token': self.gmail_credentials.refresh_token}
        if google_api_config is None:
            current_app.logger.error(f"Google API credentials not found for gmail_credentials_id: {self.gmail_credentials_id}")
            raise ValueError("Google API credentials not found for this client")
        
        openai_api_config = {'api_key': openai_credentials.openai_api_key}
        
        current_app.logger.debug(f"Creating OpenAI API manager for job: {self.id}")
        openai_api_manager = OpenAIAPIManager(api_config=openai_api_config)
        
        current_app.logger.debug(f"Creating Gmail API manager for job: {self.id}")
        gmail_client = GmailAPIManager(api_config=google_api_config)
        
        current_app.logger.debug(f"API managers successfully created for job: {self.id}")
        return openai_api_manager, gmail_client
        
    def run_job(self) -> bool:
        current_app.logger.info(f"Running job for {self}, thread_id: {self.thread_id}")
        
        current_app.logger.debug(f"Retrieving configuration for id: {self.configuration_id}")
        config = GmailIntervalFollowupConfiguration.query.get(self.configuration_id)
        if config is None:
            current_app.logger.error(f"Configuration not found for id: {self.configuration_id}")
            raise ValueError("Configuration not found")
        current_app.logger.debug(f"Configuration retrieved successfully for id: {self.configuration_id}")
        
        openai_api_manager, gmail_client = self._get_api_managers()  
        
        current_app.logger.debug(f"Generating followup prompt for thread: {self.thread_id}")
        followup_prompt = self.configuration.followup_body_prompt.format(original_transcript=self.original_transcript)
        
        current_app.logger.debug(f"Calling OpenAI API to generate followup content for thread: {self.thread_id}")
        try:
            followup_body = openai_api_manager.chat(followup_prompt, model="gpt-4o").choices[0].message.content
            current_app.logger.debug(f"Successfully generated followup content for thread: {self.thread_id}")
        except Exception as e:
            current_app.logger.error(f"Error generating followup content with OpenAI: {e}")
            raise
        
        current_app.logger.debug(f"Retrieving to_addresses for thread: {self.thread_id}")
        try:
            to_addresses = gmail_client.get_to_addresses_from_thread(self.thread_id)
            current_app.logger.debug(f"Retrieved {len(to_addresses)} recipient(s) for thread: {self.thread_id}")
        except Exception as e:
            current_app.logger.error(f"Error retrieving to_addresses for thread {self.thread_id}: {e}")
            raise
        
        current_app.logger.info(f"Creating draft for thread {self.thread_id} to {len(to_addresses)} recipient(s)")
        try:
            gmail_client.create_draft(to_addresses, config.subject_line_template, followup_body, self.thread_id)
            current_app.logger.info(f"Successfully created draft for thread: {self.thread_id}")
        except Exception as e:
            current_app.logger.error(f"Failed to create draft for thread {self.thread_id}: {e}")
            raise
            
        return True
    
    def poll(self) -> bool:
        current_app.logger.debug(f"Polling for thread: {self.thread_id}")
        try:
            openai_api_manager, gmail_client = self._get_api_managers()
            current_app.logger.debug(f"Checking if recipient responded to thread: {self.thread_id}")
            
            if gmail_client.has_recipient_responded(self.thread_id, self.gmail_credentials.user_email):
                current_app.logger.info(f"Recipient responded to thread: {self.thread_id}, stopping followup schedule")
                self.stop_schedule()
                db.session.commit()
                current_app.logger.debug(f"Successfully stopped schedule for thread: {self.thread_id}")
                return True
            else:
                current_app.logger.debug(f"No response detected for thread: {self.thread_id}, continuing followup schedule")
        except ValueError as e:
            current_app.logger.error(f"Value error while polling thread {self.thread_id}: {e}")
            return False
        except AttributeError as e:
            current_app.logger.error(f"Attribute error while polling thread {self.thread_id}: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error while polling thread {self.thread_id}: {e}", exc_info=True)
            return False
            
        return False
    