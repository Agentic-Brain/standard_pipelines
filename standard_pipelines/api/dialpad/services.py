from flask import current_app
from standard_pipelines.api.services import BaseAPIManager
from dialpad import DialpadClient
from datetime import datetime
import requests
from typing import Optional

class DialpadAPIManager(BaseAPIManager):
    def __init__(self, api_config: dict) -> None:
        super().__init__(api_config)
        self.dialpad_client = DialpadClient(api_config["api_key"])

    @property
    def required_config(self) -> list[str]:
        return ["api_key"]

    #============ API Functions =============#
    def get_transcript(self, call_id: str):
        try:
            if not call_id or not isinstance(call_id, str):
                current_app.logger.error("Invalid call_id provided.")
                return {"error": "Invalid call_id provided."}
            
            transcript = self.dialpad_client.transcript.get(call_id=call_id)
            lines = transcript.get("lines")
            if not lines:
                current_app.logger.error(f"No transcript found for call_id: {call_id}")
                return {"error": "No transcript found"}

            only_transcripts = [entry for entry in lines if entry['type'].lower() == 'transcript']
            formatted_transcript = self._format_transcript(only_transcripts)
            return {"transcript": formatted_transcript}

        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"An error occurred during API request: {e}")
            return {"error": f"An error occurred during API request: {e}"}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while getting transcript: {e}")
            return {"error": f"An unexpected error occurred while getting transcript: {e}"}
        
    def subscribe_to_call_webhook(self, hook_url: str, call_states: Optional[list[str]] = None):
        try:
            if call_states is None:
                call_states = ["hangup"]

            webhook_info = self.get_webhook_id(hook_url) # Get the webhook id if it already exists
            if 'error' in webhook_info:
                webhook_info = self.create_webhook(hook_url) # Create the webhook if it doesn't exist
                if 'error' in webhook_info:
                    return {"error": webhook_info['error']}
            
            subscription_response = self.dialpad_client.subscription.create_call_event_subscription(
                webhook_info["webhook_id"],
                call_states=call_states,
            )
            if 'error' in subscription_response:
                if subscription_response['error'].get("code") == 409:
                    current_app.logger.info(f"Webhook already subscribed to call events: {webhook_info.get('webhook_id')}")
                    return {"success": True}
                current_app.logger.error(f"Error subscribing to webhook: {subscription_response['error']}")
                return {"error": subscription_response['error']}

            current_app.logger.info(f"Subscribed to webhook: {webhook_info.get('webhook_id')}")
            return {"success": True}
        
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"An error occurred during API request: {e}")
            return {"error": f"An error occurred during API request: {e}"}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while subscribing to webhook: {e}")
            return {"error": f"An unexpected error occurred while subscribing to webhook: {e}"}
        
    def create_webhook(self, hook_url: str):
        try:
            webhook = self.dialpad_client.webhook.create_webhook(hook_url)

            if 'error' in webhook:
                webhook_code = webhook['error'].get("code")
                current_app.logger.error(f"Error creating webhook: {webhook.get('error')}")
                if webhook_code == 409:
                    return {"error": "Webhook already exists"}
                return {"error": webhook.get("error")}
             
            if webhook.get("id"):
                current_app.logger.info(f"Webhook created successfully: {webhook}")
                return {"webhook_id": webhook["id"]}  
            current_app.logger.error(f"Webhook created but id not found: {webhook}")
            return {"error": "Webhook id not found"}
        
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"An error occurred during API request: {e}")
            return {"error": f"An error occurred during API request: {e}"}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while creating webhook: {e}")
            return {"error": f"An unexpected error occurred while creating webhook: {e}"}
        
    def get_webhook_id(self, hook_url: str):
        try:
            webhooks = self.dialpad_client.webhook.list_webhooks()
            for webhook in webhooks:
                if webhook.get("hook_url") == hook_url:
                    current_app.logger.info(f"Webhook found: {webhook}")
                    if webhook.get("id"):
                        return {"webhook_id": webhook["id"]}
                    current_app.logger.error(f"Webhook found but id not found: {webhook}")
                    return {"error": "Webhook found but id not found"}
                
            current_app.logger.error(f"Webhook not found: {hook_url}")
            return {"error": "Webhook not found"}
        
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"An error occurred during API request: {e}")
            return {"error": f"An error occurred during API request: {e}"}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while getting webhook id: {e}")
            return {"error": f"An unexpected error occurred while getting webhook id: {e}"}
        
    #============ Helper Functions =============#
    def _format_transcript(self, transcript_entries: list[dict]) -> str:
        formatted_lines = []
        for entry in transcript_entries:
            time_str = entry.get('time', '')
            try:
                time_obj = datetime.fromisoformat(time_str)
                timestamp = time_obj.strftime("[%H:%M:%S]")
            except ValueError:
                timestamp = "[Unknown Time]"

            speaker = entry.get('name', 'Unknown Speaker')
            content = entry.get('content', 'N/A')

            formatted_line = f"{timestamp} {speaker}: {content}"
            formatted_lines.append(formatted_line)

        return "\n".join(formatted_lines)