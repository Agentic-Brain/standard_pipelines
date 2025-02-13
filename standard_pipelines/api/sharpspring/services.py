from flask import current_app
from standard_pipelines.api.services import BaseAPIManager
from requests.exceptions import HTTPError
import requests
import uuid

class SharpSpringAPIManager(BaseAPIManager):
    def __init__(self, api_config: dict) -> None:
        super().__init__(api_config)
        self.api_endpoint = 'https://api.sharpspring.com/pubapi/v1/'

    @property
    def required_config(self) -> list[str]:
        return ['account_id', 'secret_key']
    
    #====== API functions ======#
    def create_opportunity(self, opportunity: dict):
        try:
            required_fields = ['ownerID', 'opportunityName', 'dealStageID', 'closeDate']
            missing_fields = [field for field in required_fields if field not in opportunity]
            if missing_fields:
                current_app.logger.error(f"Missing required fields: {missing_fields}")
                return {'error': f"Missing required fields: {missing_fields}"}

            params = {'objects': [opportunity]}
            
            data = {
                'method': 'createOpportunities',
                'params': params,
                'id': str(uuid.uuid4()), #Used to track the requests, not necessary outside of async requests
                'accountID': self.api_config['account_id']
            }
            
            response = requests.post(
                self.api_endpoint,
                json=data,
                params={'secretKey': self.api_config['secret_key']}
            )
            response.raise_for_status()

            result = response.json()
            checked_result = self._check_for_errors(result)
            if "error" in checked_result:
                return {'error': checked_result["error"]}
            
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

