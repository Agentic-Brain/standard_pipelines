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
        self.first_deal_stage_id = self._get_first_deal_stage_id()

    @property
    def required_config(self) -> list[str]:
        return ['account_id', 'secret_key']
    
    #====== API functions ======#
    def create_opportunity(self, owner_email: str, client_name: str):
        try:
            owner_id_response = self._get_account_owner_id(owner_email)
            if "error" in owner_id_response:
                return owner_id_response
            
            opportunity_name = f"Sale for {client_name}"
            
            close_date = (datetime.now() + relativedelta(years=1)).strftime("%Y-%m-%d")

            opportunity = {
                "ownerID": owner_id_response["owner_id"],
                "opportunityName": opportunity_name,
                "dealStageID": self.first_deal_stage_id,
                "closeDate": close_date
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
            
            return {"success": "Opportunity created successfully"}
        
        except HTTPError as e:
            current_app.logger.error(f"HTTP error occurred while creating an opportunity: {e}")
            return {'error': f'HTTP error occurred while creating an opportunity: {e}'}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while creating an opportunity: {e}")
            return {'error': 'An unexpected error occurred while creating an opportunity'}
        
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
            params = {
                "where": {"isActive":1, "emailAddress": email},  
                "limit": 100
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
            
            return {"owner_id": owner_id}

        except HTTPError as e:
            current_app.logger.error(f"HTTP error occurred while retrieving owners: {e}")
            return {'error': f'HTTP error occurred while retrieving owners: {e}'}
        except Exception as e:
            current_app.logger.exception(f"Unexpected error retrieving owners: {e}")
            return {'error': f'Unexpected error retrieving owners: {e}'}

    def _get_first_deal_stage_id(self) -> str:
        try:
            params = {"where": {}, "limit": 100}
            data = {"method": "getDealStages", "params": params, "id": str(uuid.uuid4()),}
            
            response = requests.post(self.api_endpoint, json=data, params=self.query_params, headers={"Content-Type": "application/json"})
            response.raise_for_status()

            result = response.json()
            checked_result = self._check_for_errors(result)
            if "error" in checked_result:
                raise Exception(checked_result["error"])
            
            deal_stages = result.get("result", {}).get("dealStage", [])
            first_stage = min(deal_stages, key=lambda stage: int(stage.get("weight", float('inf'))))

            first_stage_id = first_stage.get("id")
            if not first_stage_id:
                raise Exception("No first deal stage id found")

            return first_stage_id

        except HTTPError as e:
            current_app.logger.error(f"HTTP error occurred while retrieving deal stages: {e}")
            raise HTTPError(f'HTTP error occurred while retrieving deal stages: {e}')
        except Exception as e:
            current_app.logger.exception(f"Unexpected error retrieving deal stages: {e}")
            raise Exception(f'Unexpected error retrieving deal stages: {e}')