import typing as t
from typing import Optional, Dict, Any, List
from flask import current_app
from functools import cached_property
import re

from ...api.deep_research.services import DeepResearchManager
from ...api.hubspot.models import HubSpotCredentials
from ...api.hubspot.services import HubSpotAPIManager
from ...api.openai.models import OpenAICredentials
from ..services import BaseDataFlow
from ..exceptions import InvalidWebhookError, DataFlowError
from .models import DeepResearchConfiguration


class DeepResearchFlow(BaseDataFlow[DeepResearchConfiguration]):
    """
    Data flow for analyzing LinkedIn profiles and updating HubSpot records.
    Uses the Deep Research API to extract and analyze LinkedIn data.
    """

    @classmethod
    def data_flow_name(cls) -> str:
        return "deep_research_flow"

    @cached_property
    def hubspot_api_manager(self) -> HubSpotAPIManager:
        credentials: Optional[HubSpotCredentials] = HubSpotCredentials.query.filter_by(client_id=self.client_id).first()
        if credentials is None:
            raise ValueError("No HubSpot credentials found for client")
        hubspot_config = {
            "client_id": credentials.hubspot_client_id,
            "client_secret": credentials.hubspot_client_secret,
            "refresh_token": credentials.hubspot_refresh_token
        }
        return HubSpotAPIManager(hubspot_config)

    @cached_property
    def deep_research_manager(self) -> DeepResearchManager:
        credentials = OpenAICredentials.query.filter_by(client_id=self.client_id).first()
        if credentials is None:
            raise ValueError("No OpenAI credentials found for client")
        
        # Deep Research manager uses OpenAI credentials
        config = {
            "openai_api_key": credentials.openai_api_key,
            "openai_model": self.configuration.openai_model
        }
        return DeepResearchManager(config)

    def context_from_webhook_data(self, webhook_data: t.Any) -> t.Optional[dict]:
        """
        Extract context from webhook data.
        Expected webhook format:
        {
            "eventType": "linkedin_research",
            "hubspot_record_id": "123456789",
            "linkedin_url": "https://www.linkedin.com/in/username"
        }
        """
        if not isinstance(webhook_data, dict):
            raise InvalidWebhookError('Invalid webhook data')
            
        if webhook_data.get("eventType") != "linkedin_research":
            raise InvalidWebhookError('Webhook is not for LinkedIn research')
            
        # Extract required fields
        linkedin_url = webhook_data.get("linkedin_url")
        hubspot_record_id = webhook_data.get("hubspot_record_id")
        
        if not linkedin_url or not isinstance(linkedin_url, str):
            raise InvalidWebhookError("Missing or invalid LinkedIn URL")
            
        if not hubspot_record_id or not isinstance(hubspot_record_id, str):
            raise InvalidWebhookError("Missing or invalid HubSpot record ID")
            
        # Validate LinkedIn URL format
        if not re.match(r'^https?://([a-z]+\.)?linkedin\.com/in/[a-zA-Z0-9_-]+/?$', linkedin_url):
            raise InvalidWebhookError(f"Invalid LinkedIn URL format: {linkedin_url}")
        
        return {
            "linkedin_url": linkedin_url,
            "hubspot_record_id": hubspot_record_id
        }

    def extract(self, context: t.Optional[dict] = None) -> dict:
        """
        Extract phase: Get LinkedIn data using Deep Research.
        
        Args:
            context: Contains linkedin_url and hubspot_record_id
            
        Returns:
            Dict with the extracted LinkedIn data
        """
        if not context:
            raise DataFlowError("No context provided")
            
        linkedin_url = context["linkedin_url"]
        hubspot_record_id = context["hubspot_record_id"]
        
        current_app.logger.info(f"Extracting LinkedIn data for {linkedin_url}")
        
        # Use Deep Research to analyze the LinkedIn profile
        try:
            analysis_results = self.deep_research_manager.analyze_linkedin_profile(linkedin_url)
            
            return {
                "linkedin_data": analysis_results,
                "hubspot_record_id": hubspot_record_id,
                "hubspot_record_type": self.configuration.hubspot_record_type
            }
        except Exception as e:
            current_app.logger.error(f"Error analyzing LinkedIn profile: {str(e)}", exc_info=True)
            raise DataFlowError(f"LinkedIn analysis failed: {str(e)}")

    def transform(self, data: dict, context: t.Optional[dict] = None) -> dict:
        """
        Transform phase: Map LinkedIn data to HubSpot properties.
        
        Args:
            data: Dictionary with the LinkedIn analysis data
            context: Additional context (optional)
            
        Returns:
            Dictionary with mapped HubSpot properties
        """
        linkedin_data = data["linkedin_data"]
        hubspot_record_id = data["hubspot_record_id"]
        hubspot_record_type = data["hubspot_record_type"]
        
        # Extract all data components
        profile_data = linkedin_data["profile"]
        analysis_data = linkedin_data["analysis"]
        
        # Build a comprehensive data object for mapping to HubSpot properties
        combined_data = {
            "full_name": profile_data.get("full_name", ""),
            "first_name": profile_data.get("first_name", ""),
            "last_name": profile_data.get("last_name", ""),
            "location": profile_data.get("location", ""),
            "headline": profile_data.get("headline", ""),
            "current_role": profile_data.get("current_role", ""),
            "current_company": profile_data.get("current_company", ""),
            "image_url": profile_data.get("image_url", ""),
            "profile_analysis": analysis_data.get("profile_analysis", ""),
            "posts_analysis": analysis_data.get("posts_analysis", ""),
            "comments_analysis": analysis_data.get("comments_analysis", ""),
            "summary": analysis_data.get("summary", ""),
            "linkedin_url": context["linkedin_url"] if context else ""
        }
        
        # Map to HubSpot properties based on configuration
        properties = {}
        for hubspot_property, data_field in self.configuration.properties_mapping.items():
            if data_field in combined_data:
                properties[hubspot_property] = combined_data[data_field]
                
        current_app.logger.info(f"Mapped {len(properties)} properties for HubSpot {hubspot_record_type}")
        
        return {
            "hubspot_record_id": hubspot_record_id,
            "hubspot_record_type": hubspot_record_type,
            "properties": properties
        }

    def load(self, data: dict, context: t.Optional[dict] = None) -> dict:
        """
        Load phase: Update HubSpot record with the LinkedIn data.
        
        Args:
            data: Dictionary with the mapped HubSpot properties
            context: Additional context (optional)
            
        Returns:
            Dictionary with the result of the HubSpot update
        """
        hubspot_record_id = data["hubspot_record_id"]
        hubspot_record_type = data["hubspot_record_type"]
        properties = data["properties"]
        
        current_app.logger.info(f"Updating HubSpot {hubspot_record_type} with ID: {hubspot_record_id}")
        
        # Update HubSpot record based on record type
        try:
            if hubspot_record_type == "contact":
                result = self.hubspot_api_manager.update_contact(hubspot_record_id, properties)
            elif hubspot_record_type == "company":
                result = self.hubspot_api_manager.update_company(hubspot_record_id, properties)
            elif hubspot_record_type == "deal":
                result = self.hubspot_api_manager.update_deal(hubspot_record_id, properties)
            else:
                raise DataFlowError(f"Unsupported HubSpot record type: {hubspot_record_type}")
                
            current_app.logger.info(f"Successfully updated HubSpot {hubspot_record_type}")
            
            return {
                "status": "success",
                "hubspot_record_id": hubspot_record_id,
                "hubspot_record_type": hubspot_record_type,
                "properties_updated": len(properties)
            }
        except Exception as e:
            current_app.logger.error(f"Error updating HubSpot {hubspot_record_type}: {str(e)}", exc_info=True)
            raise DataFlowError(f"HubSpot update failed: {str(e)}")