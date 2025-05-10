from flask import current_app
from standard_pipelines.api.services import BaseAPIManager
from requests.exceptions import HTTPError, RequestException, JSONDecodeError
import requests
import uuid
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
import re  # Used for phone number formatting and other string manipulations

class SharpSpringAPIManager(BaseAPIManager):
    MAX_QUERIES = 500

    def __init__(self, api_config: dict) -> None:
        super().__init__(api_config)
        self.api_endpoint = 'https://api.sharpspring.com/pubapi/v1/'
        self.query_params = {
            "accountID": self.api_config["account_id"],
            "secretKey": self.api_config["secret_key"]
        }
        self.gathered_data = {}

    @property
    def required_config(self) -> list[str]:
        return ['account_id', 'secret_key']

    #=============================== API functions ========================================#
    #====== Opportunity functions ======#
    def create_opportunity(self, owner_email: str, client_name: str, contact_id: str) -> dict:
        try:
            # Convert contact_id to string if it's not already
            if not isinstance(contact_id, str):
                contact_id = str(contact_id)

            param_check_response = self._check_for_required_params([("owner_email", owner_email, str), ("client_name", client_name, str), ("contact_id", contact_id, str)])
            if "error" in param_check_response:
                current_app.logger.error(f"Invalid parameters for create_opportunity: {param_check_response['error']}")
                return param_check_response
            
            owner_id_response = self.get_account_owner_id(owner_email)
            if "error" in owner_id_response:
                return owner_id_response
            
            first_stage_id_response = self.get_first_deal_stage_id()
            if "error" in first_stage_id_response:
                return first_stage_id_response
            
            opportunity_name = f"Sale for {client_name}"
            
            close_date = (datetime.now() + relativedelta(years=1)).strftime("%Y-%m-%d")

            opportunity = {
                "ownerID": owner_id_response["owner_id"],
                "opportunityName": opportunity_name,
                "dealStageID": first_stage_id_response["stage_id"],
                "closeDate": close_date,
                "primaryLeadID": contact_id
            }

            params = {'objects': [opportunity]}
            
            result = self._make_api_call("createOpportunities", params)
            if "error" in result:
                return result
            
            creates_list = result.get("result", {}).get("creates", []) 
            if not creates_list:
                return {"error": "No opportunity created"}
            
            created_id = creates_list[0].get("id")
            
            return {"opportunity_id": created_id}
        
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while creating an opportunity: {e}")
            return {'error': 'An unexpected error occurred while creating an opportunity'}
    
    def get_opportunity(self, id: str) -> dict:
        try:
            param_check_response = self._check_for_required_params([("id", id, str)])
            if "error" in param_check_response:
                current_app.logger.error(f"Invalid parameters for get_opportunity: {param_check_response['error']}")
                return param_check_response
            
            params = {"id": id}                
            result = self._make_api_call("getOpportunity", params)
            if "error" in result:
                return result
            
            opportunity = result.get("result", {}).get("opportunity", [])
            opportunity = opportunity[0] if opportunity else {}

            opportunity_id = opportunity.get("id")
            
            return {"opportunity_id": opportunity_id}
        
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while getting opportunity: {e}")
            return {'error': 'An unexpected error occurred while getting opportunity'}

    def get_opportunity_id_from_contact_id(self, contact_id: str) -> dict:
        try:
            param_check_response = self._check_for_required_params([("contact_id", contact_id, str)])
            if "error" in param_check_response:
                current_app.logger.error(f"Invalid parameters for get_opportunity_id_from_contact_id: {param_check_response['error']}")
                return param_check_response
            
            existing_data = self.gathered_data.get("opportunity_id")
            if existing_data:
                return {"opportunity_id": existing_data}
            
            params = {"where": {"leadID": contact_id},  "limit": 3}
            result = self._make_api_call("getOpportunityLeads", params)
            if "error" in result:
                return result
            
            opportunities = result.get("result", {}).get("getWhereopportunityLeads", [])
            opportunities = opportunities[0] if opportunities else {}

            opportunity_id = opportunities.get("id")
            if opportunity_id:
                self.gathered_data["opportunity_id"] = opportunity_id
            
            return {"opportunity_id": opportunity_id}
        
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while getting opportunity id: {e}")
            return {'error': 'An unexpected error occurred while getting opportunity id'}
        
    #====== Contact functions ======# 
    def get_account_owner_id(self, email: str) -> dict:
        try:
            param_check_response = self._check_for_required_params([("email", email, str)])
            if "error" in param_check_response:
                current_app.logger.error(f"Invalid parameters for get_account_owner_id: {param_check_response['error']}")
                return param_check_response
            
            existing_data = self.gathered_data.get("owner_id")
            if existing_data:
                return {"owner_id": existing_data}
            
            params = {
                "where": {"isActive":1, "emailAddress": email},  
                "limit": 1
            }
            result = self._make_api_call("getUserProfiles", params)
            if "error" in result:
                return result
            
            profile = result.get("result", {}).get("userProfile", [])
            if not profile:
                current_app.logger.error(f"No profile in SharpSpring for the given email found: {email}")
                return {"error": f"No profile for the given email found: {email}"}
            
            owner_id = profile[0].get("id")
            if not owner_id:
                current_app.logger.error(f"No owner id found for the given email: {email}")
                return {"error": f"No owner id found for the given email: {email}"}
            
            self.gathered_data["owner_id"] = owner_id
            return {"owner_id": owner_id}

        except Exception as e:
            current_app.logger.exception(f"Unexpected error retrieving owners: {e}")
            return {'error': f'Unexpected error retrieving owners: {e}'}
          
    def _prepare_contact_search_data(self, phone_number: str = "", name: str = None, email: str = None) -> dict:
        """
        Prepares contact data for searching by formatting the provided parameters.

        Args:
            phone_number (str, optional): The phone number to format and include in search
            name (str, optional): The name to format and include in search
            email (str, optional): The email to format and include in search

        Returns:
            dict: A dictionary containing formatted search parameters or an error message
        """
        available_data = {}

        # Format phone number if provided - this is our highest priority search field
        if phone_number and phone_number.strip():
            formatted_phone_number = self._format_phone_number(phone_number)
            if formatted_phone_number["valid"]:
                available_data["phone_number"] = formatted_phone_number["phone_number"]

        # Format email if provided - second priority
        if email:
            formatted_email = self._format_email(email)
            if formatted_email["valid"]:
                available_data["email"] = formatted_email["email"]

        # Format name if provided - lowest priority
        if name:
            formatted_name = self._format_name(name)
            if formatted_name["valid"]:
                available_data["name"] = formatted_name["name"]

        # Check if we have at least one valid search parameter
        if not available_data:
            return {"error": "No valid search parameters provided"}

        return available_data
    
    def _validate_contact_params(self, phone_number: str, name: str = None, email: str = None, max_batches: int = 3, days: int = 30) -> dict:
        """
        Validates parameters for the get_contact method.

        Args:
            phone_number (str): The phone number to search for (can be empty if email or name is provided)
            name (str, optional): The contact name to search for
            email (str, optional): The contact email to search for
            max_batches (int, optional): Maximum number of batches to fetch
            days (int, optional): Number of days back to search

        Returns:
            dict: A success response or error message
        """
        # Validate max_batches and days
        required_params = [("max_batches", max_batches, int), ("days", days, int)]
        param_check_response = self._check_for_required_params(required_params, positive_only=True)
        if "error" in param_check_response:
            current_app.logger.error(f"Invalid parameters for get_contact: {param_check_response['error']}")
            return param_check_response

        # Ensure at least one search parameter is provided
        if not (phone_number or name or email):
            return {"error": "At least one search parameter (phone_number, name, or email) must be provided"}

        # Validate types of provided parameters
        if phone_number is not None and not isinstance(phone_number, str):
            return {"error": "phone_number must be of type str"}

        if name is not None and not isinstance(name, str):
            return {"error": "name must be of type str"}

        if email is not None and not isinstance(email, str):
            return {"error": "email must be of type str"}

        return {"success": True}
        
    def get_contact(self, phone_number: str = "", name: str = None, email: str = None, max_batches: int = 3, days: int = 30) -> dict:
        """
        Gets a contact from SharpSpring using phone number, name, and/or email using direct API queries.

        Args:
            phone_number (str, optional): The phone number to search for
            name (str, optional): The contact name to search for (currently not used for direct matching)
            email (str, optional): The contact email to search for
            max_batches (int, optional): Not used in direct API approach
            days (int, optional): Not used in direct API approach

        Returns:
            dict: A dictionary containing the contact information or an error message
        """
        try:
            # Get transcript field name
            transcript_field_name = self.get_transcript_field()
            if "error" in transcript_field_name:
                return transcript_field_name

            system_name = transcript_field_name.get("system_name")

            # Only proceed if we have at least one search parameter
            if not (phone_number or email):
                return {"error": "At least one search parameter (phone_number or email) must be provided"}

            contact_id = None
            transcript = None

            # First priority: Search by email (if provided)
            if email and email.strip():
                current_app.logger.debug(f"Searching for contact by email: {email}")
                params = {
                    "where": {"emailAddress": email.strip().lower()},
                    "limit": 1,
                    "fields": ["id", "firstName", "lastName", "phoneNumber", "emailAddress", system_name]
                }

                result = self._make_api_call("getLeads", params)
                if "error" not in result:
                    leads = result.get("result", {}).get("lead", [])
                    if leads:
                        lead = leads[0]
                        contact_id = lead.get("id")
                        transcript = lead.get(system_name)
                        current_app.logger.debug(f"Found contact by email with ID: {contact_id}")
                        return {"contact_id": contact_id, "transcript": transcript}

            # Second priority: Search by phone (if provided and email search failed)
            if phone_number and phone_number.strip():
                # Format phone number by removing non-numeric characters
                formatted_phone = re.sub(r"\D", "", phone_number)
                if formatted_phone:
                    current_app.logger.debug(f"Searching for contact by phone: {formatted_phone}")
                    params = {
                        "where": {"phoneNumber": formatted_phone},
                        "limit": 1,
                        "fields": ["id", "firstName", "lastName", "phoneNumber", "emailAddress", system_name]
                    }

                    result = self._make_api_call("getLeads", params)
                    if "error" not in result:
                        leads = result.get("result", {}).get("lead", [])
                        if leads:
                            lead = leads[0]
                            contact_id = lead.get("id")
                            transcript = lead.get(system_name)
                            current_app.logger.debug(f"Found contact by phone with ID: {contact_id}")
                            return {"contact_id": contact_id, "transcript": transcript}

            # No contact found
            current_app.logger.debug(f"No contact found with provided parameters")
            return {"contact_id": None, "transcript": None}

        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while getting contact: {e}")
            return {'error': f'An unexpected error occurred while getting contact: {e}'}
        
    def create_contact(self, full_name: str, email: str, phone_number: str, owner_id: str) -> dict:
        try:
            param_check_response = self._check_for_required_params([("full_name", full_name, str), ("email", email, str), ("phone_number", phone_number, str), ("owner_id", owner_id, str)])
            if "error" in param_check_response:
                current_app.logger.error(f"Invalid parameters for create_contact: {param_check_response['error']}")
                return param_check_response
            
            first_name, last_name = full_name.split(" ", 1) if " " in full_name else (full_name, "")
            lead_data = {
                "firstName": first_name,
                "lastName": last_name,
                "emailAddress": email,  # Required field
                "phoneNumber": phone_number,
                "ownerID": owner_id,
            }

            params = {'objects': [lead_data]}
            result = self._make_api_call("createLeads", params)
            if "error" in result:
                return result

            creates_list = result.get("result", {}).get("creates", []) 
            if not creates_list:
                return {"error": "No contact created"}
            
            created_id = creates_list[0].get("id")
            return {"contact_id": created_id}
        
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while creating contact: {e}")
            return {'error': 'An unexpected error occurred while creating contact'}
        
    def update_contact_transcript(self, contact_id: str, transcript: str) -> dict:
        try:
            contact_id = str(contact_id)
            param_check_response = self._check_for_required_params([("contact_id", contact_id, str), ("transcript", transcript, str)])
            if "error" in param_check_response:
                current_app.logger.error(f"Invalid parameters for update_contact_transcript: {param_check_response['error']}")
                return param_check_response

            # Get the transcript field system name from SharpSpring
            transcript_field = self.get_transcript_field()
            if "error" in transcript_field:
                return transcript_field

            # Make sure we have the system_name
            system_name = transcript_field.get("system_name")
            if not system_name:
                current_app.logger.error("No system_name found for transcript field")
                return {"error": "No system_name found for transcript field"}

            # Update the contact with the transcript
            lead_data = {"id": contact_id, system_name: transcript}
            params = {'objects': [lead_data]}
            result = self._make_api_call("updateLeads", params)
            if "error" in result:
                return result

            update_list = result.get("result", {}).get("updates", [])
            if not update_list:
                return {"error": "No contact updated"}

            # Check for success or error in the update
            success_flag = update_list[0].get("success")
            if success_flag == "false" or success_flag is False:
                error_obj = update_list[0].get("error", {})
                error_msg = error_obj.get("message", "No contact updated")
                return {"error": error_msg}

            return {"success": True}

        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while updating contact transcript: {e}")
            return {'error': f'An unexpected error occurred while updating contact transcript: {e}'}

    #====== Field functions ======#
    def get_transcript_field(self) -> dict:
        try:
            # Check if we already have the system_name cached
            existing_system_name = self.gathered_data.get("system_name")
            existing_field_id = self.gathered_data.get("field_id")

            # If we have both pieces of data cached, return them
            if existing_system_name and existing_field_id:
                return {
                    "system_name": existing_system_name,
                    "field_id": existing_field_id
                }

            # Otherwise, look up the field from SharpSpring
            params = {"where": {"label": "Call Transcripts"}}
            result = self._make_api_call("getFields", params)
            if "error" in result:
                return result

            field_list = result.get("result", {}).get("field", [])

            # If we found the field
            if field_list:
                field = field_list[0]
                field_id = field.get("id")
                system_name = field.get("systemName")

                # Cache the values we found for future use
                if field_id:
                    self.gathered_data["field_id"] = field_id
                if system_name:
                    self.gathered_data["system_name"] = system_name

                # Return both values (either could be None)
                return {
                    "field_id": field_id,
                    "system_name": system_name
                }
            else:
                # Field doesn't exist yet
                current_app.logger.warning("Transcript field not found in SharpSpring")
                return {
                    "field_id": None,
                    "system_name": None
                }

        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while getting transcript field: {e}")
            return {'error': f'An unexpected error occurred while getting transcript field: {e}'}
        
    def create_transcript_field(self) -> dict:
        try:
            field_data = {
                "relationship": "lead",
                "label": "Call Transcripts",
                "dataType": "textarea", 
                "dataLength": 10000,    
                "isRequired": 0,          
                "isCustom": 1,            
                "isActive": 1,            
                "isAvailableInContactManager": 1,  
                "isEditableInContactManager": 1,  
                "isAvailableInForms": 0,  
            }

            params = {'objects': [field_data]}
            result = self._make_api_call("createFields", params)
            if "error" in result:
                return result

            creates_list = result.get("result", {}).get("creates", []) 
            if not creates_list:
                return {"error": "No transcript field created"}
            
            created_id = creates_list[0].get("id")
            return {"field_id": created_id}
        
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while creating transcript field: {e}")
            return {'error': 'An unexpected error occurred while creating transcript field'}
        
    #====== Deal functions ======#
    def get_first_deal_stage_id(self) -> dict:
        try:
            existing_data = self.gathered_data.get("first_deal_stage_id")
            if existing_data:
                return {"stage_id": existing_data}
            
            params = {"where": {}, "limit": 100}
            result = self._make_api_call("getDealStages", params)
            if "error" in result:
                return result
            
            deal_stages = result.get("result", {}).get("dealStage", [])
            if not deal_stages:
                current_app.logger.error("No deal stages found")
                return {'error': "No deal stages found"}

            #Get the first stage with the lowest weight, meaning it's the first stage in the pipeline
            first_stage = min(
                deal_stages, 
                key=lambda stage: float('inf') if stage.get("weight") is None else int(stage["weight"])
            )

            first_stage_id = first_stage.get("id")
            if not first_stage_id:
                current_app.logger.error("No first deal stage id found")
                return {'error': "No first deal stage id found"}

            self.gathered_data["first_deal_stage_id"] = first_stage_id
            return {"stage_id": first_stage_id}

        except Exception as e:
            current_app.logger.exception(f"Unexpected error retrieving deal stages: {e}")
            return {'error': f'Unexpected error retrieving deal stages: {e}'}

    #================================= Helper functions ========================================#
    def _make_api_call(self, method: str, params: dict) -> dict:
        try:
            param_check_response = self._check_for_required_params([("method", method, str), ("params", params, dict)])
            if "error" in param_check_response:
                current_app.logger.error(f"Invalid parameters for _make_api_call: {param_check_response['error']}")
                return param_check_response
            
            data = {"method": method, "params": params, "id": str(uuid.uuid4())}
            response = requests.post(
                self.api_endpoint, 
                json=data, 
                params=self.query_params, 
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()

            try:
                result = response.json()
            except JSONDecodeError as e:
                current_app.logger.error(f"JSON decode error in {method}: {e}")
                return {'error': f'JSON decode error in {method}: {e}'}

            return self._check_for_errors(result)

        except HTTPError as e:
            current_app.logger.error(f"HTTP error in {method}: {e}")
            return {'error': f'HTTP error in {method}: {e}'}
        except RequestException as e:
            current_app.logger.error(f"Request error in {method}: {e}")
            return {'error': 'Network error while communicating with API'}
        except Exception as e:
            current_app.logger.exception(f"Unexpected error in {method}: {e}")
            return {'error': f'Unexpected error in {method}'}
        
    def _check_for_required_params(self, params: list[tuple[str, any, type]], positive_only: bool = False) -> dict:
        for param_name, param_value, expected_type in params:
            # Check if the type matches
            if not isinstance(param_value, expected_type):
                return {"error": f"{param_name} must be of type {expected_type.__name__}"}

            # Check for None if required
            if param_value is None:
                return {"error": f"{param_name} cannot be None"}

            # Check for empty strings
            if expected_type is str and not param_value.strip():
                return {"error": f"{param_name} cannot be empty"}

            # Handle empty lists or dicts
            if isinstance(param_value, (list, dict)) and not param_value:
                return {"error": f"{param_name} cannot be empty"}

            # Handle negative values if positive_only is True
            if positive_only == True and isinstance(param_value, (int, float)) and param_value < 0:
                return {"error": f"{param_name} cannot be negative"}
            
        return {"success": True}

    def _check_for_errors(self, result: dict) -> dict:
        try:
            param_check_response = self._check_for_required_params([("result", result, dict)])
            if "error" in param_check_response:
                current_app.logger.error(f"Invalid parameters for _check_for_errors: {param_check_response['error']}")
                return param_check_response
            
            # Ensure "result" exists before proceeding
            if "result" not in result:
                current_app.logger.error(f"Malformed API response: {result}")
                return {"error": "Unexpected API response format. 'result' field is missing."}
            
            #Check for API-level errors
            if result.get("error") and isinstance(result["error"], dict):
                current_app.logger.error(f"API-level error: Code: {result['error'].get('code', 'Unknown')}, Message: {result['error'].get('message', 'Unknown')}")
                return {'error': f"{result['error'].get('message', 'Unknown')}"}
            
            # Check for object-level errors 
            method_type = "create"
            objects = result["result"].get("creates", [])
            if not objects:
                objects = result["result"].get("updates", [])
                method_type = "update"

            if objects:
                for object in objects:
                    if object.get("success") == False:
                        error_object = object.get("error", {})
                        unknown_error = "API returned a failure but did not provide an error message."
                        current_app.logger.error(f"Object-level error ({method_type}): Code: {error_object.get('code', 'Unknown')}, Message: {error_object.get('message', unknown_error)}")
                        return {'error': f"{error_object.get('message', unknown_error)}"}

            return {"result": result["result"]}
        
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while checking for errors: {e}")
            return {'error': f'An unexpected error occurred while checking for errors: {e}'}

    def _format_phone_number(self, phone_number: str) -> dict:
        if not phone_number or not isinstance(phone_number, str):
            return {"phone_number": phone_number, "valid": False}

        # Check for empty string after stripping whitespace
        if not phone_number.strip():
            return {"phone_number": phone_number, "valid": False}

        # Remove all non-numeric characters (including plus sign, parentheses, dashes, spaces)
        formatted_phone_number = re.sub(r"\D", "", phone_number)

        # Ensure we have a reasonable length for a phone number
        if len(formatted_phone_number) < 7 or len(formatted_phone_number) > 15:
            return {"phone_number": phone_number, "valid": False}

        return {"phone_number": formatted_phone_number, "valid": True}
    
    def _format_name(self, name: str) -> dict:
        if not name or not isinstance(name, str):
            return {"name": name, "valid": False}

        # Check for empty string after stripping whitespace
        if not name.strip():
            return {"name": name, "valid": False}

        # Remove leading/trailing whitespace and convert to lowercase
        formatted_name = name.strip().lower()

        # Replace multiple spaces with single space
        formatted_name = re.sub(r"\s+", " ", formatted_name)

        # Further normalization: remove non-alphabetic characters if needed
        # Commented out but available if strict matching is required
        # formatted_name = re.sub(r"[^a-z\s]", "", formatted_name)

        return {"name": formatted_name, "valid": True}
    
    def _format_email(self, email: str) -> dict:
        if not email or not isinstance(email, str):
            return {"email": email, "valid": False}

        # Check for empty string after stripping whitespace
        if not email.strip():
            return {"email": email, "valid": False}

        formatted_email = email.strip().lower()
        return {"email": formatted_email, "valid": True}

    def _find_matching_contact(self, available_data: dict, field_name: str, max_batches: int = 3, days: int = 30) -> dict:
        """
        Retrieves a contact by phone number, looking up recent contacts created or updated within a given time range.

        Args:
            available_data (dict): A dictionary containing the phone number, name, and email to search for if all are provided.
            max_batches (int): The maximum number of batches(500 contacts each) to retrieve (default 3).
            days (int): The number of days back to search for contacts (default 30).
            field_name (str): The name of the field to search for the transcript (default None).

        Returns:
            dict: A dictionary containing the contact ID and transcript or an error message if not found.
        """
        try:
            function_params = [("available_data", available_data, dict), ("max_batches", max_batches, int), ("days", days, int), ("field_name", field_name, str)]
            param_check_response = self._check_for_required_params(function_params, positive_only=True)
            if "error" in param_check_response:
                current_app.logger.error(f"Invalid parameters for _find_matching_contact: {param_check_response['error']}")
                return param_check_response

            # Check if we're looking for a contact with an email - useful for validation
            looking_for_email = available_data.get("email") and len(available_data.get("email", "")) > 0

            start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            offset = 0

            for _ in range(max_batches):
                params = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "timestamp": "create",  # Can be update to find contacts updated in the last x days
                    "limit": self.MAX_QUERIES,
                    "offset": offset,
                    "fields": ["id", "firstName", "lastName", "phoneNumber","emailAddress", "mobilePhoneNumber", field_name]
                }
                result = self._make_api_call("getLeadsDateRange", params)
                if "error" in result:
                    return result

                contacts = result.get("result", {}).get("lead", [])

                # Process in reverse order to get newest first
                for contact in reversed(contacts):
                    # Get all the fields we need for matching
                    contact_number = contact.get("phoneNumber") or contact.get("mobilePhoneNumber")
                    first_name = contact.get("firstName", "")
                    last_name = contact.get("lastName", "")
                    contact_name = first_name + last_name
                    contact_email = contact.get("emailAddress")
                    contact_id = contact.get("id")

                    # Skip any contact that doesn't have the fields we're looking for
                    # This handles the case where we're looking for a contact with an email
                    # but the current contact doesn't have one
                    if looking_for_email and not contact_email:
                        continue

                    # Skip empty contacts
                    if not contact_number and not contact_name and not contact_email:
                        continue

                    # Format the fields for comparison
                    contact_number_data = self._format_phone_number(contact_number)
                    contact_name_data = self._format_name(contact_name)
                    contact_email_data = self._format_email(contact_email)

                    # Skip invalid contacts
                    if not contact_number_data["valid"] and not contact_name_data["valid"] and not contact_email_data["valid"]:
                        continue

                    # ===============================================================
                    # PRIORITY ORDER: Phone -> Email -> Name (as specified in requirements)
                    # ===============================================================

                    # 1. PHONE MATCHING (HIGHEST PRIORITY)
                    if contact_number_data["valid"] and available_data.get("phone_number"):
                        # Don't match on empty values - this is a key requirement
                        if not contact_number_data["phone_number"].strip():
                            continue

                        # Direct phone match
                        if contact_number_data["phone_number"] == available_data.get("phone_number"):
                            current_app.logger.debug(f"[SHARPSPRING] Found contact by phone match: {contact_id}")
                            return {"contact_id": contact_id, "transcript": contact.get(field_name)}

                        # No need to check alternative phone formats since we're normalizing all numbers
                        # in the _format_phone_number method. The normalized phone numbers should match directly.

                    # 2. EMAIL MATCHING (SECOND PRIORITY)
                    if contact_email_data["valid"] and available_data.get("email"):
                        # Don't match on empty values
                        if not contact_email_data["email"].strip():
                            continue

                        # Direct email match - already normalized to lowercase
                        if contact_email_data["email"] == available_data.get("email"):
                            current_app.logger.debug(f"Found contact by email match: {contact_id}")
                            return {"contact_id": contact_id, "transcript": contact.get(field_name)}

                        # Optional: domain match if there's variation in the local part
                        contact_email_parts = contact_email_data["email"].split('@')
                        search_email_parts = available_data.get("email").lower().split('@')
                        if (len(contact_email_parts) == 2 and len(search_email_parts) == 2 and
                            contact_email_parts[1] == search_email_parts[1] and
                            (contact_email_parts[0].startswith(search_email_parts[0]) or
                             search_email_parts[0].startswith(contact_email_parts[0]))):
                            current_app.logger.debug(f"Found contact by partial email match (same domain): {contact_id}")
                            return {"contact_id": contact_id, "transcript": contact.get(field_name)}

                    # 3. NAME MATCHING (LOWEST PRIORITY)
                    if contact_name_data["valid"] and available_data.get("name"):
                        # Don't match on empty values
                        if not contact_name_data["name"].strip():
                            continue

                        # Direct normalized name match
                        if contact_name_data["name"] == available_data.get("name"):
                            current_app.logger.debug(f"Found contact by name match: {contact_id}")
                            return {"contact_id": contact_id, "transcript": contact.get(field_name)}

                        # Optional: partial name matching for first/last name combinations
                        if ' ' in first_name + ' ' + last_name and ' ' in available_data.get("name"):
                            # Get first and last names from both sides
                            contact_first = first_name.lower().strip()
                            contact_last = last_name.lower().strip()
                            search_parts = available_data.get("name").lower().split(' ', 1)
                            search_first = search_parts[0].strip()
                            search_last = search_parts[1].strip() if len(search_parts) > 1 else ""

                            # Skip empty name parts
                            if (not contact_first or not contact_last or
                                not search_first or not search_last):
                                continue

                            # Check last name match with first initial match
                            if (contact_last == search_last and
                                contact_first[0] == search_first[0]):
                                current_app.logger.debug(f"Found contact by last name + first initial match: {contact_id}")
                                return {"contact_id": contact_id, "transcript": contact.get(field_name)}

                            # Check first name match with last initial match
                            if (contact_first == search_first and
                                contact_last[0] == search_last[0]):
                                current_app.logger.debug(f"Found contact by first name + last initial match: {contact_id}")
                                return {"contact_id": contact_id, "transcript": contact.get(field_name)}

                # Move to next batch if needed
                offset += self.MAX_QUERIES
                if not contacts or len(contacts) < self.MAX_QUERIES:
                    break  # No more data left to fetch

            # No match found
            return {"contact_id": None, "transcript": None}

        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while finding matching contact: {e}")
            return {'error': f'An unexpected error occurred while finding matching contact: {e}'}
