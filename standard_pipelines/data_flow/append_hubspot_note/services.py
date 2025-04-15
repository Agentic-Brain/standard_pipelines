import typing as t
import time
from typing import Optional, Dict, List, Any, cast
from flask import current_app
from functools import cached_property

from ...api.hubspot.models import HubSpotCredentials
from ...api.hubspot.services import HubSpotAPIManager, ExtantContactHubSpotObject, ExtantDealHubSpotObject, CreatableNoteHubSpotObject
from standard_pipelines.data_flow.exceptions import APIError, InvalidWebhookError
from ..services import BaseDataFlow
from .models import AppendHubspotNoteConfiguration

# TODO: We probably wanna merge this to add_data_to_hubspot_field and overhaul that a bit
class AppendHubspotNote(BaseDataFlow[AppendHubspotNoteConfiguration]):
    """
    Data flow to append notes to HubSpot objects (contacts, deals).
    """
    
    @classmethod
    def data_flow_name(cls) -> str:
        return "append_hubspot_note"
    
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
        Extract context from webhook data for note creation.
        
        Expected webhook data format:
        {
            "object_id": "12345",
            "object_type": "contact", // or "deal"
            "notes": [
                {
                    "title": "Meeting Notes",
                    "content": "Detailed notes about the meeting..."
                }
            ]
        }
        
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
        notes = webhook_data.get('notes')
        
        # Validate required fields
        if not all([object_id, object_type, notes]):
            raise InvalidWebhookError('Missing required fields in webhook data')
        
        # Validate object_type
        if object_type not in ['contact', 'deal']:
            raise InvalidWebhookError(f'Invalid object type: {object_type}. Must be "contact" or "deal"')
        
        # Validate notes format
        if not isinstance(notes, list) or not notes:
            raise InvalidWebhookError('Notes must be a non-empty list')
        
        # Validate each note entry
        for note in notes:
            if not isinstance(note, dict):
                raise InvalidWebhookError('Each note entry must be a dictionary')
            if 'content' not in note:
                raise InvalidWebhookError('Each note entry must contain content')
        
        try:
            # Ensure object_id is an integer
            object_id_int = int(object_id)
        except (ValueError, TypeError):
            raise InvalidWebhookError('Invalid object ID format')
        
        return {
            'object_id': object_id,
            'object_type': object_type,
            'notes': notes
        }
    
    def extract(self, context: t.Optional[dict] = None) -> dict:
        """
        Verify that the requested object exists.
        
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
        notes = cast(List[Dict[str, str]], context.get('notes'))
        
        current_app.logger.info(f"Verifying {object_type} with ID {object_id} for adding {len(notes)} notes")
        
        # Verify object exists based on object_type
        try:
            if object_type == "contact":
                obj = self.hubspot_api_manager.contact_by_contact_id(str(object_id))
            elif object_type == "deal":
                obj = self.hubspot_api_manager.deal_by_deal_id(str(object_id))
            else:
                # We should never get here due to validation in context_from_webhook_data
                raise APIError(f"Unsupported object type: {object_type}")
            
            # Verify the object was found
            if not obj:
                raise APIError(f"{object_type.capitalize()} with ID {object_id} not found")
            
            return {
                'object_id': object_id,
                'object_type': object_type,
                'notes': notes,
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
    
    def create_and_associate_note(self, object_id: int, object_type: str, note_data: dict) -> dict:
        """
        Create a new note and associate it with the specified object.
        
        Args:
            object_id: The ID of the object to associate with
            object_type: The type of object (contact, deal)
            note_data: Dictionary containing note data (title and content)
            
        Returns:
            The created note object
        """
        note_title = note_data.get('title', 'Note')
        note_content = note_data.get('content', '')
        
        current_app.logger.info(f"Creating note '{note_title}' for {object_type} with ID {object_id}")
        
        # Create the note object
        note_object = CreatableNoteHubSpotObject({
            "properties": {
                "hs_note_body": note_content,
                "hs_timestamp": str(int(time.time() * 1000)),  # Current time in milliseconds
                "hs_note_title": note_title
            }
        }, self.hubspot_api_manager)
        
        try:
            # Create the note in HubSpot
            created_note = self.hubspot_api_manager.create_note(note_object)
            
            # Associate the note with the appropriate object
            if object_type == "contact":
                # Get the contact object
                contact = self.hubspot_api_manager.contact_by_contact_id(str(object_id))
                contact_obj = ExtantContactHubSpotObject(contact, self.hubspot_api_manager)
                created_note.add_association(contact_obj)
            elif object_type == "deal":
                # Get the deal object
                deal = self.hubspot_api_manager.deal_by_deal_id(str(object_id))
                deal_obj = ExtantDealHubSpotObject(deal, self.hubspot_api_manager)
                created_note.add_association(deal_obj)
                # Add owner from deal if possible
                if "hubspot_owner_id" in deal.get("properties", {}):
                    created_note.add_owner_from_deal(deal_obj)
                    
            current_app.logger.info(f"Successfully created and associated note '{note_title}' for {object_type} with ID {object_id}")
            return created_note.hubspot_object_dict
            
        except Exception as e:
            current_app.logger.error(f"Error creating note '{note_title}' for {object_type} with ID {object_id}: {str(e)}")
            raise APIError(f"Failed to create note: {str(e)}")
    
    def load(self, data: dict, context: t.Optional[dict] = None) -> dict:
        """
        Create notes and associate them with the HubSpot object.
        
        Args:
            data: The data from the transform step
            context: The context from webhook_data
            
        Returns:
            The result of the note creation operation
            
        Raises:
            APIError: If the note creation fails
        """
        object_id = cast(int, data.get('object_id'))
        object_type = cast(str, data.get('object_type'))
        notes = cast(List[Dict[str, str]], data.get('notes'))
        
        current_app.logger.info(f"Creating {len(notes)} notes for {object_type} with ID {object_id}")
        
        note_results = []
        failures = []
        
        for note_data in notes:
            try:
                created_note = self.create_and_associate_note(object_id, object_type, note_data)
                note_results.append({
                    'note_id': created_note.get('id'),
                    'note_title': note_data.get('title', 'Note'),
                    'success': True
                })
            except APIError as e:
                error_message = str(e)
                failures.append({
                    'note_title': note_data.get('title', 'Note'),
                    'success': False,
                    'error_message': error_message
                })
                current_app.logger.error(f"Error creating note: {error_message}")
        
        overall_success = len(failures) == 0
        
        current_app.logger.info(f"Completed note creation for {object_type} with ID {object_id}: {len(note_results)} succeeded, {len(failures)} failed")
        
        result = {
            'success': overall_success,
            'object_id': object_id,
            'object_type': object_type,
            'note_results': note_results,
            'failures': failures
        }
        
        # If all notes failed, raise an error
        if len(note_results) == 0 and len(failures) > 0:
            error_summaries = [f"{f.get('note_title', 'Note')}: {f['error_message']}" for f in failures]
            error_message = f"All note creations failed: {'; '.join(error_summaries)}"
            raise APIError(error_message)
        
        return result
