import typing as t
from typing import Optional, Dict, List, Any, cast
from flask import current_app
from functools import cached_property

from ...api.hubspot.models import HubSpotCredentials
from ...api.hubspot.services import HubSpotAPIManager
from standard_pipelines.data_flow.exceptions import APIError, InvalidWebhookError
from ..services import BaseDataFlow
from .models import AddDataToHubspotFieldConfiguration

class AddDataToHubspotField(BaseDataFlow[AddDataToHubspotFieldConfiguration]):
    """
    Data flow to update one or more fields in a HubSpot object.
    """
    
    @classmethod
    def data_flow_name(cls) -> str:
        return "add_data_to_hubspot_field"
    
    @staticmethod
    def format_hubspot_property_name(field_name: str) -> str:
        """
        Format field name to match HubSpot property naming conventions.
        
        HubSpot properties are lowercase with no underscores or spaces.
        
        Args:
            field_name: The original field name
            
        Returns:
            Properly formatted HubSpot property name
        """
        # Define specific mappings for common fields
        specific_mappings = {
            "first_name": "firstname",
            "last_name": "lastname",
            "email_address": "email",
            "phone_number": "phone",
            "mobile_phone": "mobilephone",
            "mobile_phone_number": "mobilephone",
        }
        
        # Check if there's a specific mapping
        if field_name in specific_mappings:
            return specific_mappings[field_name]
        
        # General formatting: lowercase and remove underscores and spaces
        formatted_name = field_name.lower().replace('_', '').replace(' ', '')
        
        return formatted_name
    
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
        data = webhook_data.get('data')
        
        # Validate required fields
        if not all([object_id, object_type, data]):
            raise InvalidWebhookError('Missing required fields in webhook data')
        
        # Validate data format
        if not isinstance(data, list) or not data:
            raise InvalidWebhookError('Data must be a non-empty list of field updates')
        
        # Validate each field update entry
        for field_entry in data:
            if not isinstance(field_entry, dict):
                raise InvalidWebhookError('Each data entry must be a dictionary')
            if not all(key in field_entry for key in ['field_name', 'field_contents']):
                raise InvalidWebhookError('Each data entry must contain field_name and field_contents')
        
        try:
            # Ensure object_id is an integer
            object_id_int = int(object_id)
        except (ValueError, TypeError):
            raise InvalidWebhookError('Invalid object ID format')
        
        return {
            'object_id': object_id,
            'object_type': object_type,
            'field_updates': data
        }
    
    def extract(self, context: t.Optional[dict] = None) -> dict:
        """
        Verify that the requested object exists and the fields are valid.
        
        Args:
            context: The context from webhook_data
            
        Returns:
            A dictionary with the verified data
            
        Raises:
            APIError: If the object doesn't exist
            ValueError: If context is missing
        """
        if not context:
            raise ValueError("Context is required")
        
        object_id = cast(int, context.get('object_id'))
        object_type = cast(str, context.get('object_type'))
        field_updates = cast(List[Dict[str, str]], context.get('field_updates'))
        
        current_app.logger.info(f"Verifying {object_type} with ID {object_id} for multiple field updates")
        
        # Verify object exists based on object_type
        try:
            if object_type == "contact":
                obj = self.hubspot_api_manager.contact_by_contact_id(str(object_id))
            elif object_type == "deal":
                obj = self.hubspot_api_manager.deal_by_deal_id(str(object_id))
            else:
                # For other object types, we'll need to implement specific verification
                # This is a placeholder for future expansion
                raise APIError(f"Verification for {object_type} not implemented")
            
            # Verify the object was found
            if not obj:
                raise APIError(f"{object_type.capitalize()} with ID {object_id} not found")
            
            
            return {
                'object_id': object_id,
                'object_type': object_type,
                'field_updates': field_updates,
                'original_object': obj
            }
        except APIError as e:
            current_app.logger.error(f"API Error verifying {object_type} with ID {object_id}: {str(e)}")
            raise
        except ValueError as e:
            current_app.logger.error(f"Value Error verifying {object_type} with ID {object_id}: {str(e)}")
            raise APIError(f"Invalid value for {object_type} with ID {object_id}: {str(e)}")
        except Exception as e:
            current_app.logger.error(f"Error verifying {object_type} with ID {object_id}: {str(e)}")
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
        # For this data flow, we just pass through the data
        return data
    
    def load(self, data: dict, context: t.Optional[dict] = None) -> dict:
        """
        Update the fields in the HubSpot object.
        
        Args:
            data: The data from the transform step
            context: The context from webhook_data
            
        Returns:
            The result of the update operation
            
        Raises:
            APIError: If the update fails
        """
        object_id = cast(int, data.get('object_id'))
        object_type = cast(str, data.get('object_type'))
        field_updates = cast(List[Dict[str, str]], data.get('field_updates'))
        
        current_app.logger.info(f"Updating {object_type} with ID {object_id}, processing {len(field_updates)} field updates")
        
        update_results = []
        failures = []
        last_updated_object = None
        
        for update in field_updates:
            field_name = cast(str, update.get('field_name'))
            field_value = cast(str, update.get('field_contents'))
            
            # Format the field name according to HubSpot conventions
            hubspot_field_name = self.format_hubspot_property_name(field_name)
            
            current_app.logger.info(f"Updating field {field_name} as HubSpot property '{hubspot_field_name}' with value: {field_value}")
            
            try:
                # Use the update_field method to update the field
                updated_object = self.hubspot_api_manager.update_field(
                    object_type=object_type,
                    object_id=object_id,
                    field_name=hubspot_field_name,
                    field_value=field_value
                )
                
                last_updated_object = updated_object
                update_results.append({
                    'field_name': field_name,
                    'hubspot_property': hubspot_field_name,
                    'field_value': field_value,
                    'success': True
                })
            except APIError as e:
                error_message = str(e)
                # Handle property doesn't exist errors
                if "PROPERTY_DOESNT_EXIST" in error_message:
                    property_name = hubspot_field_name
                    # Extract the property name from the error if available
                    if "Property \"" in error_message and "\" does not exist" in error_message:
                        start_index = error_message.find("Property \"") + 10
                        end_index = error_message.find("\" does not exist")
                        if start_index > 0 and end_index > start_index:
                            property_name = error_message[start_index:end_index]
                    
                    failure_details = {
                        'field_name': field_name,
                        'hubspot_property': hubspot_field_name,
                        'field_value': field_value,
                        'success': False,
                        'error_type': 'PROPERTY_DOESNT_EXIST',
                        'error_message': f"Property '{property_name}' doesn't exist in HubSpot. Check if you need a custom property created first."
                    }
                # Handle validation errors
                elif "VALIDATION_ERROR" in error_message:
                    failure_details = {
                        'field_name': field_name,
                        'hubspot_property': hubspot_field_name,
                        'field_value': field_value,
                        'success': False,
                        'error_type': 'VALIDATION_ERROR',
                        'error_message': f"Value '{field_value}' is not valid for property '{hubspot_field_name}'. {error_message}"
                    }
                # Handle other errors
                else:
                    failure_details = {
                        'field_name': field_name,
                        'hubspot_property': hubspot_field_name,
                        'field_value': field_value,
                        'success': False,
                        'error_type': 'GENERAL_ERROR',
                        'error_message': error_message
                    }
                    
                current_app.logger.error(f"Error updating field {field_name}: {failure_details['error_message']}")
                failures.append(failure_details)
        
        # Determine overall success based on failures
        overall_success = len(failures) == 0
        
        current_app.logger.info(f"Completed updates for {object_type} with ID {object_id}: {len(update_results)} succeeded, {len(failures)} failed")
        
        result = {
            'success': overall_success,
            'object_id': object_id,
            'object_type': object_type,
            'update_results': update_results,
            'failures': failures
        }
        
        if last_updated_object:
            result['updated_object'] = last_updated_object
        
        # If all updates failed, raise an error
        if len(update_results) == 0 and len(failures) > 0:
            error_summaries = [f"{f['field_name']}: {f['error_message']}" for f in failures]
            error_message = f"All field updates failed: {'; '.join(error_summaries)}"
            raise APIError(error_message)
        
        return result
