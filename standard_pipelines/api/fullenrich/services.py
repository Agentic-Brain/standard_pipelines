from standard_pipelines.api.services import BaseAPIManager
from flask import current_app
from requests.exceptions import HTTPError, RequestException
import requests
import typing as t
import time

class FullEnrichAPIManager(BaseAPIManager):
    def __init__(self, api_config: dict) -> None:
        super().__init__(api_config)
        self.base_url = "https://app.fullenrich.com/api/v1"
        self._api_key_verified = False

    @property
    def required_config(self) -> list[str]:
        return ["api_key"]
    
    #=======================================================================#
    #========================== API functions ==============================#

    def enrich_contact(self, field_data: dict[str, str], webhook_url: t.Optional[str] = None) -> dict:
        try:
            if not self.ensure_api_key():
                return {"error": "Invalid API key, cannot proceed with enrichment"}
            
            valid_data = {"enrich_fields": ["contact.emails", "contact.phones"]}

            possible_fields = ["firstname", "lastname", "domain", "company_name", "linkedin_url"]
            for field in possible_fields:
                if field in field_data and isinstance(field_data[field], str) and field_data[field].strip():
                    valid_data[field] = field_data[field].strip()

            if "firstname" not in valid_data or "lastname" not in valid_data:
                current_app.logger.error("firstname and lastname are required to enrich contact")
                return {"error": "firstname and lastname are required to enrich contact"}

            if "domain" not in valid_data and "company_name" not in valid_data:
                current_app.logger.error("domain or company_name are required to enrich contact")
                return {"error": "domain or company_name are required to enrich contact"}

            url = f"{self.base_url}/contact/enrich/bulk"
            headers = {
                "Authorization": f"Bearer {self.api_config['api_key']}",
                "Content-Type": "application/json"
            }

            payload = {
                "name": f"Enrichment for {valid_data['firstname']} {valid_data['lastname']}",
                "datas": [valid_data]
            }

            if webhook_url and isinstance(webhook_url, str) and webhook_url.strip() and (webhook_url.startswith("http://") or webhook_url.startswith("https://")):
                payload["webhook_url"] = webhook_url

            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            return {"enrichment_id": result["enrichment_id"]}
        
        except HTTPError as e:
            current_app.logger.error(f"An HTTP error occurred while enriching contact: {e}")
            return {"error": f"An HTTP error occurred while enriching contact: {e}"}
        except RequestException as e:
            current_app.logger.error(f"An API request error occurred while enriching contact: {e}")
            return {"error": f"An API request error occurred while enriching contact: {e}"}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while enriching contact: {e}")
            return {"error": f"An unexpected error occurred while enriching contact: {e}"}
        

    def get_enrichment_results(self, enrichment_id: str, attempts: int = 5, delay: int = 60) -> dict:
        try:
            for _ in range(attempts):
                if not isinstance(enrichment_id, str) or not enrichment_id.strip():
                    current_app.logger.error("Invalid enrichment_id provided")
                    return {"error": "Invalid enrichment_id provided"}

                url = f"{self.base_url}/contact/enrich/bulk/{enrichment_id}"
                headers = {
                    "Authorization": f"Bearer {self.api_config['api_key']}",
                    "Content-Type": "application/json"
                }

                response = requests.get(url, headers=headers)
                response.raise_for_status()
                result = response.json()
                if 'status' in result:
                    if result['status'] == 'FINISHED':
                        contact_info = result.get('datas', [{}])[0].get('contact', {})
                        phone_number = contact_info.get('most_probable_phone', "")
                        email = contact_info.get('most_probable_email', "")

                        return {"phone_number": phone_number, "email": email}
                    
                    elif result['status'] == 'IN_PROGRESS':
                        time.sleep(delay)
                        continue
                else:
                    current_app.logger.error(f"Unexpected data received: {result}")
                    return {"error": f"Unexpected data received: {result}"}

            # If max attempts are reached without success
            current_app.logger.error(f"Max attempts reached. Enrichment results could not be retrieved for {enrichment_id}")
            return {"error": f"Max attempts reached. Enrichment results could not be retrieved for {enrichment_id}"}

        except HTTPError as e:
            current_app.logger.error(f"An HTTP error occurred while getting enrichment results: {e}")
            return {"error": f"An HTTP error occurred while getting enrichment results: {e}"}
        except RequestException as e:
            current_app.logger.error(f"An API request error occurred while getting enrichment results: {e}")
            return {"error": f"An API request error occurred while getting enrichment results: {e}"}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while getting enrichment results: {e}")
            return {"error": f"An unexpected error occurred while getting enrichment results: {e}"}

    #=======================================================================#
    #========================== Helper functions ===========================#

    def _verify_api_key(self):
        try:
            url = f"{self.base_url}/account/keys/verify"
            headers = {
                "Authorization": f"Bearer {self.api_config['api_key']}",
                "Content-Type": "application/json"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            return {"Valid": True}
        
        except HTTPError as e:
            error_message = response.json().get("message", "Unknown error")
            if response.status_code == 401:
                current_app.logger.error(f"Invalid API key provided: {error_message}")
                return {"error": f"Invalid API key provided: {error_message}"}
            
            current_app.logger.error(f"An HTTP error occurred while verifying API key: {error_message}")
            return {"error": f"An HTTP error occurred while verifying API key: {error_message}"}
        
        except RequestException as e:
            current_app.logger.error(f"An API request error occurred while verifying API key: {e}")
            return {"error": f"An API request error occurred while verifying API key: {e}"}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while verifying API key: {e}")
            return {"error": f"An unexpected error occurred while verifying API key: {e}"}

    def ensure_api_key(self):
        if not self._api_key_verified:
            result = self._verify_api_key()
            if "error" in result:
                return False
            self._api_key_verified = True
            return True
        return True