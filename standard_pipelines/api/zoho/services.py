from __future__ import annotations
import json
import time
import typing as t

from flask import current_app
from standard_pipelines.api.services import BaseAPIManager
from standard_pipelines.data_flow.exceptions import APIError
from standard_pipelines.extensions import oauth

from zohocrmsdk.src.com.zoho.crm.api import Initializer, ParameterMap, HeaderMap
from zohocrmsdk.src.com.zoho.crm.api.dc import USDataCenter
from zohocrmsdk.src.com.zoho.api.authenticator import OAuthToken
from zohocrmsdk.src.com.zoho.crm.api.util import APIResponse, Choice
from zohocrmsdk.src.com.zoho.crm.api.record.api_exception import APIException

# Zoho Record API imports
from zohocrmsdk.src.com.zoho.crm.api.record import (
    RecordOperations,
    BodyWrapper,
    Record as ZCRMRecord,
    GetRecordsParam,
    SearchRecordsParam,
    Field
)
from zohocrmsdk.src.com.zoho.crm.api.record.action_wrapper import ActionWrapper

from zohocrmsdk.src.com.zoho.crm.api.users import UsersOperations

from abc import ABCMeta, abstractmethod
from types import MappingProxyType

from .models import ZohoCredentials

class ZohoAPIManager(BaseAPIManager, metaclass=ABCMeta):
    def __init__(self, creds: ZohoCredentials) -> None:
        super().__init__(creds)
        environment = USDataCenter.PRODUCTION()
        self.token: OAuthToken = OAuthToken(
            client_id=creds.oauth_client_id,
            client_secret=creds.oauth_client_secret,
            refresh_token=creds.oauth_refresh_token,
            access_token=creds.oauth_access_token
        )
        # there's an error in zoho, expires_in is actually expires_at
        if creds.oauth_expires_at:
            self.token.set_expires_in(str(creds.oauth_expires_at))
        current_app.logger.debug(f"Created OAuthToken with client_id: {creds.oauth_client_id}")
        # initialize the Zoho CRM SDK (this sets a thread-local client)
        try:
            Initializer.initialize(environment=environment, token=self.token)
            current_app.logger.info("Successfully initialized Zoho CRM SDK")
        except Exception as e:
            current_app.logger.error(f"Failed to initialize Zoho CRM SDK: {str(e)}", exc_info=True)
            raise

    @property
    def required_config(self) -> list[str]:
        return ["client_id", "oauth_client_id", "oauth_client_secret"]

    @property
    def access_token(self) -> str:
        # Refresh token if expired.
        expires_at: int = int(self.token.get_expires_in())
        cur_time_ms: int = int(time.time() * 1000)
        if cur_time_ms >= expires_at:
            current_app.logger.info("Access token expired, refreshing...")
            try:
                # Import the OAuth client from the zohocrmsdk
                from zohocrmsdk.src.com.zoho.api.authenticator.oauth_token import OAuthToken
                from zohocrmsdk.src.com.zoho.crm.api.user_signature import UserSignature
                
                # Refresh the token
                refreshed_token = self.token.refresh()
                
                # Update the SDK Initializer with the refreshed token
                user_signature = UserSignature(None)  # You might want to set an email here if needed
                Initializer.initialize(
                    user_signature=user_signature,
                    environment=USDataCenter.PRODUCTION(),
                    token=refreshed_token
                )
                
                current_app.logger.info("Successfully refreshed access token")
            except Exception as e:
                current_app.logger.error(f"Failed to refresh access token: {str(e)}", exc_info=True)
                raise
        return self.token.get_access_token()

    def _serialize_zoho_object(self, zoho_obj: t.Any) -> t.Union[dict, list, str, None]:
        """
        Convert a Zoho object into a JSON-serializable format.
        
        Args:
            zoho_obj: Any Zoho object that needs to be serialized
            
        Returns:
            A JSON-serializable version of the object (dict, list, str, or None)
        """
        if zoho_obj is None:
            return None
            
        # Handle objects with key-value pairs
        if hasattr(zoho_obj, 'get_key_values'):
            result = {}
            for key, value in zoho_obj.get_key_values().items():
                result[key] = self._serialize_zoho_object(value)
            return result
            
        # Handle lists/tuples
        if isinstance(zoho_obj, (list, tuple)):
            return [self._serialize_zoho_object(item) for item in zoho_obj]
            
        # Handle basic types by converting to string
        return str(zoho_obj)

    def get_contact_by_field(self, search_params: dict, match_all: bool = False) -> t.Optional[dict]:
        """
        Retrieves a contact by various fields (phone, email, or name).
        
        Args:
            search_params: Dictionary containing search parameters.
                Supported keys: 'phone', 'email', 'first_name', 'last_name'
            match_all: If True, all criteria must match (AND).
                      If False, any criteria can match (OR).
            
        Returns:
            The contact data as a JSON-serializable dictionary, or None if no contact is found
        """
        current_app.logger.info(f"Searching for contact with params: {search_params} (match_all={match_all})")
        record_ops = RecordOperations("Contacts")
        param_instance = ParameterMap()

        # Build search criteria
        criteria_parts = []
        if phone := search_params.get('phone'):
            criteria_parts.append(f"(Phone:equals:{phone})")
        if email := search_params.get('email'):
            criteria_parts.append(f"(Email:equals:{email})")
        if first_name := search_params.get('first_name'):
            criteria_parts.append(f"(First_Name:equals:{first_name})")
        if last_name := search_params.get('last_name'):
            criteria_parts.append(f"(Last_Name:equals:{last_name})")

        if not criteria_parts:
            raise ValueError("At least one search parameter must be provided")

        # Combine criteria with either AND or OR operator
        operator = " and " if match_all else " or "
        search_criteria = operator.join(criteria_parts)
        param_instance.add(SearchRecordsParam.criteria, search_criteria)
        
        try:
            response = record_ops.search_records(param_instance)
            current_app.logger.debug(f"get_contact_by_field: {response.get_status_code()}, {response.get_object()}")
            
            # Check if response object is an APIException
            if isinstance(response.get_object(), APIException):
                error = response.get_object()
                error_message = error.get_message().get_value() if isinstance(error.get_message(), Choice) else str(error.get_message())
                raise APIError(f"Zoho API Error: {error_message}")
            
            if response.get_status_code() == 204:
                return None
            
            if response.get_object() and hasattr(response.get_object(), 'get_data'):
                contacts = response.get_object().get_data()
                if contacts:
                    return self._serialize_zoho_object(contacts[0])
            return None
            
        except Exception as e:
            current_app.logger.exception(f"Error searching for contact: {e}")
            raise APIError(f"Error searching for contact: {str(e)}")

    def get_all_contacts(self) -> list[dict]:
        current_app.logger.info("Fetching all contacts")
        record_ops = RecordOperations("Contacts")
        params = GetRecordsParam()
        params.set_page(1)
        params.set_per_page(200)
        
        try:
            response = record_ops.get_records("Contacts", params)
            records = []
            if response.get_object():
                data = response.get_object().get_data()
                records = [record.to_dict() for record in data]
                current_app.logger.info(f"Successfully retrieved {len(records)} contacts")
            else:
                current_app.logger.warning("No contacts found in response")
            return records
        except Exception as e:
            current_app.logger.error(f"Error fetching contacts: {str(e)}", exc_info=True)
            raise APIError(f"Failed to fetch contacts: {str(e)}")

    def get_all_owners(self) -> list[dict]:
        users_ops = UsersOperations()
        response = users_ops.get_users()
        owners = []
        if response.get_object():
            data = response.get_object().get_users()
            for user in data:
                owners.append(user.to_dict())
        return owners

    def get_all_users(self) -> list[dict]:
        # In Zoho, owners and users are essentially the same.
        return self.get_all_owners()

    def get_contact_by_contact_id(self, contact_id: str, properties: list[str] = []) -> dict:
        record_ops = RecordOperations("Contacts")
        response = record_ops.get_record(int(contact_id), "Contacts")
        if response.get_object() and response.get_object().get_data():
            return self._serialize_zoho_object(response.get_object().get_data()[0])
        else:
            raise APIError(f"Contact with id {contact_id} not found.")

    def get_deal_by_deal_id(self, deal_id: str, properties: list[str] = []) -> dict:
        record_ops = RecordOperations("Deals")
        response = record_ops.get_record(int(deal_id), "Deals")
        if response.get_object() and response.get_object().get_data():
            return self._serialize_zoho_object(response.get_object().get_data()[0])
        else:
            raise APIError(f"Deal with id {deal_id} not found.")

    def get_user_by_email(self, email: str) -> dict:
        users = self.get_all_owners()
        matching_users = []
        for user in users:
            user_email = user.get("email")
            if not user_email:
                current_app.logger.warning(f"Zoho user {user.get('id')} has no email.")
            elif user_email.lower() == email.lower():
                matching_users.append(user)
        if len(matching_users) > 1:
            raise APIError(f"Multiple users found for email {email}.")
        if not matching_users:
            raise APIError(f"No user found for email {email}.")
        return matching_users[0]
    
    def get_deal_by_contact_id(self, contact_id: str) -> dict:
        # In Zoho, assume the deal has a lookup field "Contact_Name" linking to a contact.
        record_ops = RecordOperations()
        params = SearchRecordsParam()
        # Use criteria to search for deals where the "Contact_Name" field equals the given contact_id.
        params.set_criteria(f"(Contact_Name:equals:{contact_id})")
        response = record_ops.search_records("Deals", params)
        if response.get_object() and response.get_object().get_data():
            deals = response.get_object().get_data()
            if len(deals) > 1:
                raise APIError(f"Multiple deals found for contact {contact_id}.")
            return deals[0].to_dict()
        else:
            raise APIError(f"No deal found for contact {contact_id}.")

    def zoho_association_object(self, to_id: str, association_id: str, association_category: str = "ZOHO_DEFINED") -> dict:
        # This method is retained for compatibility, but note that in Zoho associations
        # are typically handled via lookup fields rather than a separate API call.
        return {
            "to": {"id": to_id},
            "types": [{
                "associationCategory": association_category,
                "associationTypeId": association_id,
            }]
        }

    def create_record(self, module_name: str, record_data: dict, parent_record: dict = None) -> dict:
        """
        Creates a record in Zoho CRM for any module type.
        
        Args:
            module_name: The module name in Zoho CRM (e.g., "Contacts", "Deals", "Meetings", "Notes")
            record_data: Dictionary containing the record data to be created
            parent_record: Optional parent record to associate with (required for Notes)
                           Format: {'id': '123456', 'module': 'Deals'}
            
        Returns:
            The created record data as a JSON-serializable dictionary
            
        Raises:
            APIError: If the record creation fails
        """
        current_app.logger.info(f"Creating {module_name} record with data: {record_data}")
        
        # Import necessary classes for related records
        from zohocrmsdk.src.com.zoho.crm.api.record import Record, BodyWrapper
        from zohocrmsdk.src.com.zoho.crm.api.record import RecordOperations
        
        # Initialize the record operations with the module name
        record_ops = RecordOperations(module_name)
        
        # Create a new record object
        record = Record()
        
        # Add all fields from the record_data dictionary to the record
        for key, value in record_data.items():
            record.add_key_value(key, value)
        
        # Handle special case for Notes - they need a parent record
        if module_name == "Notes" and parent_record:
            if not parent_record.get('id') or not parent_record.get('module'):
                raise APIError("Parent record must have 'id' and 'module' fields for Notes")
            
            parent_id = parent_record['id']
            parent_module = parent_record['module']
            
            try:
                # Create a parent record object properly for the Zoho SDK
                parent_record_obj = Record()
                parent_record_obj.set_id(parent_id)
                
                # Set the parent record directly (this format works with Zoho)
                record.add_key_value("Parent_Id", parent_record_obj)
                record.add_key_value("$se_module", parent_module)
                
                # These are important for Notes
                record.add_key_value("Note_Title", record_data.get("Note_Title", "Note"))
                record.add_key_value("Note_Content", record_data.get("Note_Content", ""))
            except Exception as e:
                current_app.logger.error(f"Error setting up parent record: {e}")
                raise APIError(f"Error setting up parent record: {str(e)}")
        
        # Create the request body wrapper
        request = BodyWrapper()
        request.set_data([record])
        
        try:
            # Send the create request
            response = record_ops.create_records(request)
            current_app.logger.debug(f"create_record response: {response.get_status_code()}, {response.get_object()}")
            
            # Check for errors
            if response.get_status_code() >= 400:
                if isinstance(response.get_object(), ActionWrapper):
                    action_wrapper = response.get_object()
                    if action_wrapper.get_data():
                        for action_response in action_wrapper.get_data():
                            if isinstance(action_response, APIException):
                                error = action_response
                                error_message = f"Code: {error.get_code()}, Details: {error.get_details()}"
                                current_app.logger.error(f"Error creating {module_name} record: {error_message}")
                                raise APIError(f"Failed to create {module_name}: {error_message}")
                
                raise APIError(f"Failed to create {module_name} record. Status code: {response.get_status_code()}")
            
            # Process successful response
            if response.get_object() and hasattr(response.get_object(), 'get_data'):
                created_records = response.get_object().get_data()
                if created_records:
                    created_record = created_records[0]
                    current_app.logger.info(f"Successfully created {module_name} record with ID: {created_record.get_details().get('id')}")
                    return self._serialize_zoho_object(created_record)
            
            raise APIError(f"Failed to create {module_name} record. No data returned.")
            
        except Exception as e:
            current_app.logger.exception(f"Error creating {module_name} record: {e}")
            if isinstance(e, APIError):
                raise
            raise APIError(f"Error creating {module_name} record: {str(e)}")

    def create_note(self, note_data: dict, parent_record_id: str, parent_module: str) -> dict:
        """
        Creates a note in Zoho CRM with proper parent record association.
        
        Args:
            note_data: Dictionary containing the note data (Note_Title, Note_Content)
            parent_record_id: ID of the parent record (e.g., Deal or Contact ID)
            parent_module: Module of the parent record (e.g., "Deals", "Contacts")
            
        Returns:
            The created note data as a JSON-serializable dictionary
            
        Raises:
            APIError: If the note creation fails
        """
        current_app.logger.info(f"Creating note for {parent_module} with ID {parent_record_id}")
        
        try:
            # For Zoho CRM API v2, we'll use the native API instead of trying to use the SDK
            # which has complicated requirements for parent records
            
            # Set up headers and base URL
            headers = {
                "Authorization": f"Zoho-oauthtoken {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Prepare the data
            data = {
                "data": [
                    {
                        "Note_Title": note_data.get("Note_Title", "Note"),
                        "Note_Content": note_data.get("Note_Content", ""),
                        "Parent_Id": {
                            "id": str(parent_record_id),
                            "module": parent_module
                        },
                        "$se_module": parent_module
                    }
                ]
            }
            
            # Make the direct API call
            import requests
            url = "https://www.zohoapis.com/crm/v2/Notes"
            
            response = requests.post(url, headers=headers, json=data)
            
            # Process the response
            if response.status_code >= 400:
                error_data = response.json()
                error_message = error_data.get('message', 'Unknown error')
                current_app.logger.error(f"Error creating note: {error_message}")
                raise APIError(f"Failed to create note: {error_message}")
            
            # Return the created note
            response_data = response.json()
            if response_data.get('data') and len(response_data['data']) > 0:
                created_note = response_data['data'][0]
                current_app.logger.info(f"Successfully created note with ID: {created_note.get('details', {}).get('id')}")
                return created_note
            
            raise APIError("Failed to create note. No data returned.")
        
        except Exception as e:
            current_app.logger.exception(f"Error creating note: {e}")
            if isinstance(e, APIError):
                raise
            raise APIError(f"Error creating note: {str(e)}")
