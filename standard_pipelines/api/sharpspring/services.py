from flask import current_app
from standard_pipelines.api.services import BaseAPIManager
from requests.exceptions import HTTPError, RequestException, JSONDecodeError 
import requests
import uuid
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta


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
    def create_opportunity(self, owner_email: str, client_name: str, contact_id: str):
        try:
            owner_id_response = self._get_account_owner_id(owner_email)
            if "error" in owner_id_response:
                return owner_id_response
            
            first_stage_id_response = self._get_first_deal_stage_id()
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

    #====== Contact functions ======#   
    def get_contact_by_phone_number(self, phone_number: str, max_batches: int = 3, days: int = 30) -> dict:
        """
        Retrieves a contact by phone number, looking up recent contacts created or updated within a given time range.
        
        Args:
            phone_number (str): The phone number to search for.
            max_batches (int): The maximum number of batches(500 contacts each) to retrieve (default 3).
            days (int): The number of days back to search for contacts (default 30).
            
        Returns:
            dict: A dictionary containing the contact ID and transcript or an error message if not found.
        """
        try:
            transcript_field_name = self.get_transcript_field()
            if "error" in transcript_field_name:
                return transcript_field_name
        
            formatted_phone_number = self._format_phone_number(phone_number)
            if not formatted_phone_number["valid"]:
                return {"error": "Invalid phone number"}

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
                    "fields": ["id", "firstName", "lastName", "phoneNumber", "mobilePhoneNumber", transcript_field_name["system_name"]]
                }
                result = self._make_api_call("getLeadsDateRange", params)
                if "error" in result:
                    return result
                
                contacts = result.get("result", {}).get("lead", [])

                for contact in reversed(contacts): #Reversed to get the newest contacts first
                    # Get phone number
                    contact_number = contact.get("phoneNumber") or contact.get("mobilePhoneNumber")
                    if not contact_number:
                        continue
                    
                    # Format phone number
                    contact_number = self._format_phone_number(contact_number)
                    if not contact_number["valid"]:
                        continue
                    
                    # Match phone numbers
                    if contact_number["phone_number"] == formatted_phone_number["phone_number"]:
                        contact_id = contact.get("id")
                        transcript = contact.get(transcript_field_name["system_name"])                
                        return {"contact_id": contact_id, "transcript": transcript}
                
                offset += self.MAX_QUERIES  
                if not contacts or len(contacts) < self.MAX_QUERIES:
                    break  # No more data left to fetch
            
            return {"error": "No contact found"}

        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while getting recent contacts: {e}")
            return {'error': 'An unexpected error occurred while getting recent contacts'}
        
    def create_contact(self, full_name: str, email: str, phone_number: str, owner_id: str) -> dict:
        try:
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

    #================================= Helper functions ========================================#
    def _make_api_call(self, method: str, params: dict) -> dict:
        try:
            data = {"method": method, "params": params, "id": str(uuid.uuid4())}
            response = requests.post(
                self.api_endpoint, json=data, params=self.query_params, headers={"Content-Type": "application/json"}
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

    def _check_for_errors(self, result: dict) -> dict:
        try:
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
                    if object.get("success") == "false":
                        error_object = object.get("error", {})
                        unknown_error = "API returned a failure but did not provide an error message."
                        current_app.logger.error(f"Object-level error ({method_type}): Code: {error_object.get('code', 'Unknown')}, Message: {error_object.get('message', unknown_error)}")
                        return {'error': f"{error_object.get('message', unknown_error)}"}

            return {"result": result["result"]}
        
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while checking for errors: {e}")
            return {'error': f'An unexpected error occurred while checking for errors: {e}'}
    
    def _get_account_owner_id(self, email: str) -> dict:
        try:
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

    def _get_first_deal_stage_id(self) -> dict:
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

            first_stage = min(deal_stages, key=lambda stage: int(stage.get("weight", float('inf'))))

            first_stage_id = first_stage.get("id")
            if not first_stage_id:
                current_app.logger.error("No first deal stage id found")
                return {'error': "No first deal stage id found"}

            self.gathered_data["first_deal_stage_id"] = first_stage_id
            return {"stage_id": first_stage_id}

        except Exception as e:
            current_app.logger.exception(f"Unexpected error retrieving deal stages: {e}")
            return {'error': f'Unexpected error retrieving deal stages: {e}'}
        
    def _get_opportunity_id_from_contact_id(self, contact_id: str) -> dict:
        try:
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

    def _format_phone_number(self, phone_number: str) -> dict:
        if not phone_number or not isinstance(phone_number, str):
            return {"phone_number": phone_number, "valid": False}
        
        formatted_phone_number = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")
        if len(formatted_phone_number) < 10:
            return {"phone_number": phone_number, "valid": False}
        
        if len(formatted_phone_number) > 10:
            formatted_phone_number = formatted_phone_number[-10:]
        return {"phone_number": formatted_phone_number, "valid": True}

