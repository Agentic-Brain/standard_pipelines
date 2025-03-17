from standard_pipelines.api.services import BaseManualAPIManager
from standard_pipelines.data_flow.exceptions import APIError
from typing import Optional, Dict, Any, List
from flask import current_app
import requests
import json


class RapidAPIManager(BaseManualAPIManager):
    """Manager for RapidAPI services."""
    
    @property
    def required_config(self) -> list[str]:
        return ["rapidapi_key", "rapidapi_host"]
    
    def api_url(self, api_context: Optional[dict] = None) -> str:
        """Get the RapidAPI URL based on the context."""
        host = self.api_config['rapidapi_host']
        endpoint = api_context.get('endpoint', '') if api_context else ''
        return f"https://{host}/{endpoint}"
        
    def https_headers(self, api_context: Optional[dict] = None) -> Optional[dict]:
        """Get headers for RapidAPI request."""
        return {
            'x-rapidapi-key': self.api_config['rapidapi_key'],
            'x-rapidapi-host': self.api_config['rapidapi_host']
        }
    
    def https_method(self, api_context: Optional[dict] = None) -> str:
        """Override the default method to use GET for RapidAPI calls."""
        return api_context.get('method', 'GET') if api_context else 'GET'
    
    def https_parameters(self, api_context: Optional[dict] = None) -> Optional[dict]:
        """Get parameters for RapidAPI request."""
        if api_context and 'params' in api_context:
            return api_context['params']
        return None
    
    def make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, method: str = 'GET') -> Dict[str, Any]:
        """
        Make a request to a RapidAPI endpoint.
        
        Args:
            endpoint: The endpoint path to append to the base URL
            params: Query parameters for the request
            method: HTTP method (GET, POST, etc.)
            
        Returns:
            Dict[str, Any]: The JSON response as a dictionary
        """
        api_context = {
            'endpoint': endpoint,
            'params': params,
            'method': method
        }
        
        try:
            response = self.get_response(api_context)
            return response.json()
        except requests.RequestException as e:
            current_app.logger.error(f"RapidAPI request failed: {str(e)}")
            raise APIError(f"RapidAPI request failed: {str(e)}")
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Failed to parse JSON response: {str(e)}")
            raise APIError(f"Failed to parse JSON from RapidAPI response: {str(e)}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error in RapidAPI request: {str(e)}")
            raise APIError(f"Unexpected error in RapidAPI request: {str(e)}")