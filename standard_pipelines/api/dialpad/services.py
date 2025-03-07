from flask import current_app
from .models import DialpadCredentials
from standard_pipelines.api.services import BaseAPIManager
from dialpad import DialpadClient
from datetime import datetime
import pytz
from requests.exceptions import RequestException, HTTPError
from typing import Optional

class DialpadAPIManager(BaseAPIManager):
    def __init__(self, creds : dict) -> None:
        super().__init__(creds)
        self.dialpad_client = DialpadClient(creds.api_key)

    @property
    def required_config(self) -> list[str]:
        return ["api_key"]

    #============ API Functions =============#
    def get_transcript(self, call_data: dict, timezone: str = "UTC"):
        try:
            call_id = call_data.get("call_id")
            if not isinstance(call_id, (str, int)):
                current_app.logger.error("Invalid call_id provided.")
                return {"error": "Invalid call_id provided."}
            call_id = str(call_id)
            
            transcript = self.dialpad_client.transcript.get(call_id=call_id)
            lines = transcript.get("lines")
            if not lines:
                current_app.logger.error(f"No transcript found for call_id: {call_id}")
                return {"error": "No transcript found"}

            only_transcripts = [entry for entry in lines if entry.get('type', '').lower() == 'transcript']
            participants = self._get_call_participants(call_data)
            formatted_transcript = self._format_transcript(only_transcripts, call_data, participants, timezone)
            return {"transcript": formatted_transcript, "participants": participants}

        except HTTPError as e:
            current_app.logger.error(f"An HTTP error occurred while getting transcript: {e}")
            return {"error": f"An HTTP error occurred while getting transcript: {e}"}
        except RequestException as e:
            current_app.logger.error(f"An API request error occurred while getting transcript: {e}")
            return {"error": f"An API request error occurred while getting transcript: {e}"}
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
        
        except HTTPError as e:
            current_app.logger.error(f"An HTTP error occurred while subscribing to webhook: {e}")
            return {"error": f"An HTTP error occurred while subscribing to webhook: {e}"}
        except RequestException as e:
            current_app.logger.error(f"An API request error occurred while subscribing to webhook: {e}")
            return {"error": f"An API request error occurred while subscribing to webhook: {e}"}
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
        
        except HTTPError as e:
            current_app.logger.error(f"An HTTP error occurred while creating webhook: {e}")
            return {"error": f"An HTTP error occurred while creating webhook: {e}"}
        except RequestException as e:
            current_app.logger.error(f"An API request error occurred while creating webhook: {e}")
            return {"error": f"An API request error occurred while creating webhook: {e}"}
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
        
        except HTTPError as e:
            current_app.logger.error(f"An HTTP error occurred while getting webhook id: {e}")
            return {"error": f"An HTTP error occurred while getting webhook id: {e}"}
        except RequestException as e:
            current_app.logger.error(f"An API request error occurred while getting webhook id: {e}")
            return {"error": f"An API request error occurred while getting webhook id: {e}"}
        except Exception as e:
            current_app.logger.exception(f"An unexpected error occurred while getting webhook id: {e}")
            return {"error": f"An unexpected error occurred while getting webhook id: {e}"}
        
    #============ Helper Functions =============#
    def _format_transcript(self, transcript_entries: list[dict], call_data: dict, participants: dict, timezone: str = "UTC") -> str:
        formatted_lines = []

        date_started = datetime.fromtimestamp(call_data.get('date_started') / 1000, tz=pytz.UTC) if call_data.get('date_started') else None
        call_id = call_data.get('call_id', 'Unknown Call ID')

        try:
            local_timezone = pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            local_timezone = pytz.UTC

        if date_started:
            date_started = date_started.astimezone(local_timezone)

        formatted_lines.append(f"Organizer: {participants['host']['email']}")
        formatted_lines.append(f"Attendee: {participants['guest']['email']}")
        formatted_lines.append(f"Call Date: {date_started.strftime('%Y-%m-%d %H:%M:%S') if date_started else 'Unknown'}")
        formatted_lines.append(f"Call ID: {call_id}")

        for entry in transcript_entries:
            time_str = entry.get('time', '')
            try:
                time_obj = datetime.fromisoformat(time_str).replace(tzinfo=pytz.UTC).astimezone(local_timezone)
                timestamp = time_obj.strftime("[%H:%M:%S]")
            except ValueError:
                timestamp = "[Unknown Time]"

            speaker = entry.get('name', 'Unknown Speaker')
            content = entry.get('content', 'N/A')

            formatted_line = f"{timestamp} {speaker}: {content}"
            formatted_lines.append(formatted_line)

        return "\n".join(formatted_lines)
    
    def _get_call_participants(self, call_data: dict) -> dict:
        guest = {
            "name": call_data.get("contact", {}).get("name", "Unknown Caller"),
            "email": call_data.get("contact", {}).get("email", ""),
            "phonenumber": call_data.get("contact", {}).get("phone", "")
        }

        host = {
            "name": call_data.get("target", {}).get("name", "Unknown Host"),
            "email": call_data.get("target", {}).get("email", ""),
            "phonenumber": call_data.get("target", {}).get("phone", "")
        }

        return {"guest": guest, "host": host}