import typing as t
from typing import Optional
from flask import current_app
from functools import cached_property

from ...api.hubspot.models import HubSpotCredentials
from ...api.hubspot.services import HubSpotAPIManager
from standard_pipelines.data_flow.exceptions import APIError, InvalidWebhookError
from ..services import BaseDataFlow
from .models import AddDataToHubspotFieldConfiguration

class AddDataToHubspotField(BaseDataFlow[AddDataToHubspotFieldConfiguration]):
    """
    Data flow to update a field in a HubSpot object.
    """
    
    @classmethod
    def data_flow_name(cls) -> str:
        return "add_data_to_hubspot_field"
    
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
    
    def context_from_webhook_data(self, webhook_data: t.Any) -> t.Optional[dict]:
        """
        Extract context from webhook data.
        
        Args:
            webhook_data: The webhook data to process
            
        Returns:
            A dictionary with the extracted context or None if no action is needed
            
        Raises:
            InvalidWebhookError: If the webhook data is invalid
        """
        if not isinstance(webhook_data, dict):
            raise InvalidWebhookError('Invalid webhook data')
        
        # Extract required fields
        object_id = webhook_data.get('object_id')
        object_type = webhook_data.get('object_type')
        field_name = webhook_data.get('field_name')
        field_value = webhook_data.get('field_value')
        
        # Validate required fields
        if not all([object_id, object_type, field_name, field_value]):
            raise InvalidWebhookError('Missing required fields in webhook data')
        
        try:
            # Ensure object_id is an integer
            object_id = int(object_id)
        except (ValueError, TypeError):
            raise InvalidWebhookError('Invalid object ID format')
        
        return {
            'object_id': object_id,
            'object_type': object_type,
            'field_name': field_name,
            'field_value': field_value
        }
    
    def extract(self, context: t.Optional[dict] = None) -> dict:
        """
        Verify that the requested object exists and the field is valid.
        
        Args:
            context: The context from webhook_data
            
        Returns:
            A dictionary with the verified data
            
        Raises:
            APIError: If the object doesn't exist or the field is invalid
        """
        if not context:
            raise ValueError("Context is required")
        
        object_id = context.get('object_id')
        object_type = context.get('object_type')
        field_name = context.get('field_name')
        field_value = context.get('field_value')
        
        current_app.logger.info(f"Verifying {object_type} with ID {object_id} and field {field_name}")
        
        # Verify object exists based on object_type
        try:
            if object_type == "contacts":
                obj = self.hubspot_api_manager.contact_by_contact_id(str(object_id))
            elif object_type == "deals":
                obj = self.hubspot_api_manager.deal_by_deal_id(str(object_id))
            else:
                # For other object types, we'll need to implement specific verification
                # This is a placeholder for future expansion
                raise APIError(f"Verification for {object_type} not implemented")
            
            # Verify the object was found
            if not obj:
                raise APIError(f"{object_type.capitalize()} with ID {object_id} not found")
            
            # Check if the field exists in the properties
            properties = obj.get('properties', {})
            if field_name not in properties and field_name not in obj:
                current_app.logger.warning(f"Field {field_name} not found in {object_type} properties")
                # We don't raise an error here as HubSpot allows setting new properties
            
            return {
                'object_id': object_id,
                'object_type': object_type,
                'field_name': field_name,
                'field_value': field_value,
                'original_object': obj
            }
        except Exception as e:
            current_app.logger.error(f"Error verifying {object_type} with ID {object_id}: {str(e)}")
            if isinstance(e, APIError):
                raise
            raise APIError(f"Failed to verify {object_type} with ID {object_id}: {str(e)}")
    
    def transform(self, data: dict, context: t.Optional[dict] = None) -> dict:
        """
        Transform the extracted data for loading.
        
        Args:
            data: The data from the extract step
            context: The context from webhook_data
            
        Returns:
            The transformed data ready for loading
        """
        # For this simple data flow, we just pass through the data
        return data
    
    def load(self, data: dict, context: t.Optional[dict] = None) -> dict:
        """
        Update the field in the HubSpot object.
        
        Args:
            data: The data from the transform step
            context: The context from webhook_data
            
        Returns:
            The result of the update operation
            
        Raises:
            APIError: If the update fails
        """
        object_id = data.get('object_id')
        object_type = data.get('object_type')
        field_name = data.get('field_name')
        field_value = data.get('field_value')
        
        current_app.logger.info(f"Updating {object_type} with ID {object_id}, setting {field_name}={field_value}")
        
        try:
            # Use the update_field method to update the field
            updated_object = self.hubspot_api_manager.update_field(
                object_type=object_type,
                object_id=object_id,
                field_name=field_name,
                field_value=field_value
            )
            
            current_app.logger.info(f"Successfully updated {object_type} with ID {object_id}")
            
            return {
                'success': True,
                'object_id': object_id,
                'object_type': object_type,
                'field_name': field_name,
                'field_value': field_value,
                'updated_object': updated_object
            }
        except Exception as e:
            current_app.logger.error(f"Error updating {object_type} field {field_name}: {str(e)}")
            if isinstance(e, APIError):
                raise
            raise APIError(f"Failed to update {field_name} for {object_type} with ID {object_id}: {str(e)}")
