from flask import current_app
from standard_pipelines.api.services import BaseAPIManager
from requests.exceptions import HTTPError, RequestException, JSONDecodeError 
import requests
import uuid
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
import re

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
          
    def get_contact(self, phone_number: str, name: str = None, email: str = None, max_batches: int = 3, days: int = 30) -> dict:
        try:
            function_params = [("phone_number", phone_number, str),("max_batches", max_batches, int),("days", days, int),]
            if name:
                function_params.append(("name", name, str))
            if email:
                function_params.append(("email", email, str))

            param_check_response = self._check_for_required_params(function_params)
            if "error" in param_check_response:
                current_app.logger.error(f"Invalid parameters for get_contact_by_phone_number: {param_check_response['error']}")
                return param_check_response
            
            transcript_field_name = self.get_transcript_field()
            if "error" in transcript_field_name:
                return transcript_field_name

            available_data = {}
            formatted_phone_number = self._format_phone_number(phone_number)
            if formatted_phone_number["valid"]:
                available_data["phone_number"] = formatted_phone_number["phone_number"]
            
            # Only format and send to search function if name and email are provided
            if name:
                formatted_name = self._format_name(name)
                if formatted_name["valid"]:
                    available_data["name"] = formatted_name["name"]
            if email:
                formatted_email = self._format_email(email)
                if formatted_email["valid"]:
                    available_data["email"] = formatted_email["email"]

            if not available_data:
                return {"error": "Invalid phone number and name provided"}
            
            contact_data = self._find_matching_contact(available_data, transcript_field_name["system_name"], max_batches, days)
            if "error" in contact_data:
                current_app.logger.warning(f"Could not find contact with phone number: {phone_number}")
                return contact_data
            
            return contact_data

        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while getting recent contacts: {e}")
            return {'error': 'An unexpected error occurred while getting recent contacts'}
        
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
            param_check_response = self._check_for_required_params([("contact_id", contact_id, str), ("transcript", transcript, str)])
            if "error" in param_check_response:
                current_app.logger.error(f"Invalid parameters for update_contact_transcript: {param_check_response['error']}")
                return param_check_response
            
            transcript_field_name = self.get_transcript_field()
            if "error" in transcript_field_name:
                return transcript_field_name

            lead_data = {"id": contact_id, transcript_field_name["system_name"]: transcript}
            params = {'objects': [lead_data]}
            result = self._make_api_call("updateLeads", params)
            if "error" in result:
                return result

            update_list = result.get("result", {}).get("updates", []) 
            if not update_list:
                return {"error": "No contact updated"}
            
            if update_list[0].get("success") == "false":
                return {"error": update_list[0].get("error", {}).get("message", "No contact updated")}
            
            return {"success": True}
        
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while creating contact: {e}")
            return {'error': 'An unexpected error occurred while creating contact'}

    #====== Field functions ======#
    def get_transcript_field(self) -> dict:
        try:
            existing_data = self.gathered_data.get("system_name")
            if existing_data:
                return {"system_name": existing_data}
            
            params = {"where": {"label": "Call Transcripts"}}
            result = self._make_api_call("getFields", params)
            if "error" in result:
                return result
            
            field_list = result.get("result", {}).get("field", [])
            field = field_list[0] if field_list else {}
            
            field_id = field.get("id")
            system_name = field.get("systemName")

            self.gathered_data["system_name"] = system_name
            return {"field_id": field_id, "system_name": system_name}
        
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while getting contact: {e}")
            return {'error': 'An unexpected error occurred while getting contact'}
        
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
        
        formatted_phone_number = re.sub(r"\D", "", phone_number) 
        
        if len(formatted_phone_number) < 7 or len(formatted_phone_number) > 15:
            return {"phone_number": phone_number, "valid": False}

        return {"phone_number": formatted_phone_number, "valid": True}
    
    def _format_name(self, name: str) -> dict:
        if not name or not isinstance(name, str):
            return {"name": name, "valid": False}
        
        # Remove all non-alphabetic characters and spaces
        formatted_name = re.sub(r"[^a-zA-Z]", "", name).lower()
        
        return {"name": formatted_name, "valid": True}
    
    def _format_email(self, email: str) -> dict:
        if not email or not isinstance(email, str):
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

                for contact in reversed(contacts): #Reversed to get the newest contacts first
                    contact_number = contact.get("phoneNumber") or contact.get("mobilePhoneNumber")
                    contact_name = contact.get("firstName","") + contact.get("lastName","")
                    contact_email = contact.get("emailAddress")

                    if not contact_number and not contact_name and not contact_email:
                        continue

                    contact_number = self._format_phone_number(contact_number)
                    contact_name = self._format_name(contact_name)
                    contact_email = self._format_email(contact_email)

                    if not contact_number["valid"] and not contact_name["valid"] and not contact_email["valid"]:
                        continue
                    
                    is_phone_match = contact_number["phone_number"] == available_data.get("phone_number")
                    is_name_match = contact_name["name"] == available_data.get("name")
                    is_email_match = contact_email["email"] == available_data.get("email")

                    if is_phone_match or is_name_match or is_email_match:
                        contact_id = contact.get("id")
                        transcript = contact.get(field_name)   

                        current_app.logger.info(f"Found contact {contact}")

                        return {"contact_id": contact_id, "transcript": transcript}
                
                offset += self.MAX_QUERIES  
                if not contacts or len(contacts) < self.MAX_QUERIES:
                    break  # No more data left to fetch
            
            return {"error": "No contact found"}

        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while finding matching contact: {e}")
            return {'error': f'An unexpected error occurred while finding matching contact: {e}'}

