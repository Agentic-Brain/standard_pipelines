from flask import current_app
from standard_pipelines.api.services import BaseAPIManager
from requests.exceptions import HTTPError
import requests
import uuid
from datetime import datetime
from dateutil.relativedelta import relativedelta


class SharpSpringAPIManager(BaseAPIManager):
    def __init__(self, api_config: dict) -> None:
        super().__init__(api_config)
        self.api_endpoint = 'https://api.sharpspring.com/pubapi/v1/'
        self.query_params = {
            "accountID": self.api_config["account_id"],
            "secretKey": self.api_config["secret_key"]
        }
        self.first_deal_stage_id = None
        self.owner_id = None

    @property
    def required_config(self) -> list[str]:
        return ['account_id', 'secret_key']

    #====== API functions ======#
    def create_opportunity(self, owner_email: str, client_name: str, client_id: str):
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
                "primaryLeadID": client_id
            }

            params = {'objects': [opportunity]}
            data = {
                'method': 'createOpportunities',
                'params': params,
                'id': str(uuid.uuid4()), #Used to track the requests, not necessary outside of async requests
            }

            response = requests.post(
                self.api_endpoint,
                json=data,
                params=self.query_params,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            result = response.json()
            checked_result = self._check_for_errors(result)
            if "error" in checked_result:
                return checked_result
            
            creates_list = data.get("result", {}).get("creates", []) 
            if not creates_list:
                return {"error": "No opportunity created"}
            
            created_id = creates_list[0].get("id")
            
            return {"opportunity_id": created_id}
        
        except HTTPError as e:
            current_app.logger.error(f"HTTP error occurred while creating an opportunity: {e}")
            return {'error': f'HTTP error occurred while creating an opportunity: {e}'}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while creating an opportunity: {e}")
            return {'error': 'An unexpected error occurred while creating an opportunity'}
    
    def get_opportunity(self, id: str) -> dict:
        try:
            params = {"id": id}
            data = {"method": "getOpportunity", "params": params, "id": str(uuid.uuid4()),}
            
            response = requests.post(self.api_endpoint, json=data, params=self.query_params, headers={"Content-Type": "application/json"})
            response.raise_for_status()

            result = response.json()
            checked_result = self._check_for_errors(result)
            if "error" in checked_result:
                return checked_result
            
            opportunity = result.get("result", {}).get("opportunity", [])
            opportunity = opportunity[0] if opportunity else {}

            opportunity_id = opportunity.get("id")
            
            return {"opportunity_id": opportunity_id}
        
        except HTTPError as e:
            current_app.logger.error(f"HTTP error occurred while getting opportunity: {e}")
            return {'error': f'HTTP error occurred while getting opportunity: {e}'}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while getting opportunity: {e}")
            return {'error': 'An unexpected error occurred while getting opportunity'}

    def get_contact_by_email(self, client_email: str) -> dict:
        try:
            params = {
                "where": {"emailAddress": client_email},
                "limit": 1,
                "fields": ["id", "firstName", "lastName", "emailAddress", "phoneNumber", "mobilePhoneNumber", "companyName"]
            }
            data = {"method": "getLeads", "params": params, "id": str(uuid.uuid4()),}
            
            response = requests.post(self.api_endpoint, json=data, params=self.query_params, headers={"Content-Type": "application/json"})
            response.raise_for_status()

            result = response.json()
            checked_result = self._check_for_errors(result)
            if "error" in checked_result:
                return checked_result
            
            contact_list = result.get("result", {}).get("lead", [])
            contact = contact_list[0] if contact_list else {}
    
            return {"contact": contact}
        
        except HTTPError as e:
            current_app.logger.error(f"HTTP error occurred while getting contact: {e}")
            return {'error': f'HTTP error occurred while getting contact: {e}'}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while getting contact: {e}")
            return {'error': 'An unexpected error occurred while getting contact'}
    
    def create_contact(self, full_name: str, email: str, phone_number: str, owner_id: str) -> dict:
        try:
            first_name, last_name = full_name.split(" ", 1) if " " in full_name else (full_name, "")
            lead_data = {
                "firstName": first_name,
                "lastName": last_name,
                "emailAddress": email,  # Required field
                "phoneNumber": phone_number,
                "ownerID": owner_id
            }

            params = {'objects': [lead_data]}
            data = {"method": "createLeads", "params": params, "id": str(uuid.uuid4()),}
            
            response = requests.post(self.api_endpoint, json=data, params=self.query_params, headers={"Content-Type": "application/json"})
            response.raise_for_status()

            result = response.json()
            checked_result = self._check_for_errors(result)
            if "error" in checked_result:
                return checked_result

            creates_list = data.get("result", {}).get("creates", []) 
            if not creates_list:
                return {"error": "No contact created"}
            
            created_id = creates_list[0].get("id")
            return {"contact_id": created_id}
        
        except HTTPError as e:
            current_app.logger.error(f"HTTP error occurred while creating contact: {e}")
            return {'error': f'HTTP error occurred while creating contact: {e}'}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while creating contact: {e}")
            return {'error': 'An unexpected error occurred while creating contact'}
        
    #====== Helper functions ======#
    def _check_for_errors(self, result: dict) -> dict:
        try:
            #Check for API-level errors
            if result.get("error"):
                current_app.logger.error(f"API-level error: Code: {result['error'].get('code', 'Unknown')}, Message: {result['error'].get('message', 'Unknown')}")
                return {'error': f"{result['error'].get('message', 'Unknown')}"}

            # Check for object-level errors 
            if result.get("result") and "creates" in result["result"]:
                if not result["result"]["creates"]:
                    raise ValueError("API returned a failure but did not provide an error message.")
                for create in result["result"]["creates"]:
                    if create.get("success") == "false":
                        error_object = create.get("error")
                        if error_object:
                            current_app.logger.error(f"Object-level error: Code: {error_object.get('code', 'Unknown')}, Message: {error_object.get('message', 'Unknown')}")
                            return {'error': f"{error_object.get('message', 'Unknown')}"}
                        else:
                            raise ValueError("API returned a failure but did not provide an error message.")
                        
            return {"result": result}
        
        except ValueError as e:
            current_app.logger.error(f"An error occurred while checking for errors: {e}")
            return {'error': str(e)}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while checking for errors: {e}")
            return {'error': f'An unexpected error occurred while checking for errors: {e}'}
    
    def _get_account_owner_id(self, email: str) -> dict:
        try:
            if self.owner_id is not None:
                return {"owner_id": self.owner_id}
            
            params = {
                "where": {"isActive":1, "emailAddress": email},  
                "limit": 1
            }
            data = {"method": "getUserProfiles", "params": params, "id": str(uuid.uuid4()),}
            
            response = requests.post(self.api_endpoint, json=data, params=self.query_params, headers={"Content-Type": "application/json"})
            response.raise_for_status()

            result = response.json()
            checked_result = self._check_for_errors(result)
            if "error" in checked_result:
                return checked_result
            
            profile = result.get("result", {}).get("userProfile", [])
            if not profile:
                current_app.logger.error(f"No profile in SharpSpring for the given email found: {email}")
                return {"error": f"No profile for the given email found: {email}"}
            
            owner_id = profile[0].get("id")
            if not owner_id:
                current_app.logger.error(f"No owner id found for the given email: {email}")
                return {"error": f"No owner id found for the given email: {email}"}
            
            self.owner_id = owner_id
            return {"owner_id": owner_id}

        except HTTPError as e:
            current_app.logger.error(f"HTTP error occurred while retrieving owners: {e}")
            return {'error': f'HTTP error occurred while retrieving owners: {e}'}
        except Exception as e:
            current_app.logger.exception(f"Unexpected error retrieving owners: {e}")
            return {'error': f'Unexpected error retrieving owners: {e}'}

    def _get_first_deal_stage_id(self) -> str:
        try:
            if self.first_deal_stage_id is not None:
                return {"stage_id": self.first_deal_stage_id}
            
            params = {"where": {}, "limit": 100}
            data = {"method": "getDealStages", "params": params, "id": str(uuid.uuid4()),}
            
            response = requests.post(self.api_endpoint, json=data, params=self.query_params, headers={"Content-Type": "application/json"})
            response.raise_for_status()

            result = response.json()
            checked_result = self._check_for_errors(result)
            if "error" in checked_result:
                current_app.logger.error(checked_result["error"])
                return checked_result
            
            deal_stages = result.get("result", {}).get("dealStage", [])
            first_stage = min(deal_stages, key=lambda stage: int(stage.get("weight", float('inf'))))

            first_stage_id = first_stage.get("id")
            if not first_stage_id:
                current_app.logger.error("No first deal stage id found")
                return {'error': "No first deal stage id found"}

            self.first_deal_stage_id = first_stage_id
            return {"stage_id": first_stage_id}

        except HTTPError as e:
            current_app.logger.error(f"HTTP error occurred while retrieving deal stages: {e}")
            return {'error': f'HTTP error occurred while retrieving deal stages: {e}'}
        except Exception as e:
            current_app.logger.exception(f"Unexpected error retrieving deal stages: {e}")
            return {'error': f'Unexpected error retrieving deal stages: {e}'}
        
    def _get_opportunity_id_from_contact_id(self, contact_id: str) -> dict:
        try:
            params = {"where": {"leadID": contact_id},  "limit": 3}
            data = {"method": "getOpportunityLeads", "params": params, "id": str(uuid.uuid4()),}
            
            response = requests.post(self.api_endpoint, json=data, params=self.query_params, headers={"Content-Type": "application/json"})
            response.raise_for_status()

            result = response.json()
            checked_result = self._check_for_errors(result)
            if "error" in checked_result:
                return checked_result
            
            opportunities = result.get("result", {}).get("getWhereopportunityLeads", [])
            opportunities = opportunities[0] if opportunities else {}

            opportunity_id = opportunities.get("id")
            
            return {"opportunity_id": opportunity_id}
        
        except HTTPError as e:
            current_app.logger.error(f"HTTP error occurred while getting opportunity id: {e}")
            return {'error': f'HTTP error occurred while getting opportunity id: {e}'}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while getting opportunity id: {e}")
            return {'error': 'An unexpected error occurred while getting opportunity id'}