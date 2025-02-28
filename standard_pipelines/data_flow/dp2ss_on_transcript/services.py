from ..utils import BaseDataFlow
from ..exceptions import InvalidWebhookError, APIError
from .models import DP2SSOnTranscriptConfiguration
from functools import cached_property
import typing as t

from ...api.openai.services import OpenAIAPIManager
from ...api.openai.models import OpenAICredentials

from ...api.sharpspring.services import SharpSpringAPIManager
from ...api.sharpspring.models import SharpSpringCredentials

from ...api.dialpad.services import DialpadAPIManager
from ...api.dialpad.models import DialpadCredentials



class DP2SSOnTranscript(BaseDataFlow[DP2SSOnTranscriptConfiguration]):

    OPENAI_SUMMARY_MODEL = "gpt-4o"

    @classmethod
    def data_flow_name(cls) -> str:
        return "dp2ss_on_transcript"
    
    @cached_property
    def sharpspring_api_manager(self) -> SharpSpringAPIManager:
        credentials = SharpSpringCredentials.query.filter_by(client_id=self.client_id).first()
        if credentials is None:
            raise ValueError("No SharpSpring credentials found for client")
        sharpspring_config = {
            "account_id": credentials.account_id,
            "secret_key": credentials.secret_key
        }
        return SharpSpringAPIManager(sharpspring_config)

    @cached_property
    def dialpad_api_manager(self) -> DialpadAPIManager:
        credentials = DialpadCredentials.query.filter_by(client_id=self.client_id).first()
        if credentials is None:
            raise ValueError("No Dialpad credentials found for client")
        dialpad_config = {
            "api_key": credentials.dialpad_api_key
        }
        return DialpadAPIManager(dialpad_config)

    @cached_property
    def openai_api_manager(self) -> OpenAIAPIManager:
        credentials = OpenAICredentials.query.filter_by(client_id=self.client_id).first()
        if credentials is None:
            raise ValueError("No OpenAI credentials found for client")
        openai_config = {
            "api_key": credentials.openai_api_key
        }
        return OpenAIAPIManager(openai_config)
    
    #======================== Core Flow ==============================#
    def context_from_webhook_data(self, webhook_data: t.Any) -> t.Optional[dict]:
        if not isinstance(webhook_data, dict):
            raise InvalidWebhookError('Invalid webhook data')
        if webhook_data.get("state") != "hangup":
            raise InvalidWebhookError('Invalid webhook type')
        
        required_fields = {
            "date_started": "Date started is required",
            "call_id": "Call ID is required",
            "contact": "Contact is required",
            "target": "Target is required"
        }

        for field, error_message in required_fields.items():
            if webhook_data.get(field) is None:
                raise InvalidWebhookError(error_message)
        
        call_data = {
            "date_started": webhook_data["date_started"],
            "call_id": webhook_data["call_id"],
            "contact": webhook_data["contact"],
            "target": webhook_data["target"],
        }
        return call_data

    #Attempt to gather all the data we need from our source systems
    def extract(self, context: t.Optional[dict] = None) -> dict:
        transcript = self.dialpad_api_manager.get_transcript(context)
        if "error" in transcript:
            raise APIError(transcript["error"])
        
        #Get the owner ID
        owner_email = context["target"]["email"]
        owner_id_response = self.sharpspring_api_manager.get_account_owner_id(owner_email)
        if "error" in owner_id_response:
            raise APIError(owner_id_response["error"])
        
        #Get the contact ID
        contact = context["contact"]
        contact_id_response = self.sharpspring_api_manager.get_contact(contact["phone"], contact["name"], contact["email"])
        if "error" in contact_id_response:
            raise APIError(contact_id_response["error"])
        
        #Check if the field to hold the transcript exists
        field_response = self.sharpspring_api_manager.get_transcript_field()
        if "error" in field_response:
            raise APIError(field_response["error"])

        #Get the opportunity ID
        if contact_id_response.get("contact_id"): #Required for getting the opportunity id
            opportunity_id_response = self.sharpspring_api_manager.get_opportunity_id_from_contact_id(contact_id_response["contact_id"])
            if "error" in opportunity_id_response:
                raise APIError(opportunity_id_response["error"])
        else:
            opportunity_id_response = {"opportunity_id": None}

        data ={
            "transcript": transcript["transcript"],
            "existing_transcript": contact_id_response["transcript"],
            "contact_id": contact_id_response["contact_id"],
            "owner_id": owner_id_response["owner_id"],
            "field_id": field_response["field_id"],
            "opportunity_id": opportunity_id_response["opportunity_id"]
        }
        
        return data
    
    #Takes in extracted data and applies client-specific transformations
    def transform(self, data: dict, context: t.Optional[dict] = None) -> dict:
        summary = self.meeting_summary(data["transcript"])

        #If the transcript already exists, we append it to the new summary
        if data["existing_transcript"]:
            summary = f"{summary}\n\n#=====================#\n\n{data['existing_transcript']}"

        data["summary"] = summary

        return data

    #Loads the transformed data into the target system
    def load(self, data: dict, context: t.Optional[dict] = None) -> None:
        # Things are created based on if data for them could be extracted in the extract step or not

        # Creates the contact if contact doesn't exist
        data["contact_id"] = self.ensure_contact_id(data)

        # Creates the transcript field if it doesn't exist
        data["field_id"] = self.ensure_transcript_field(data)

        # Creates the opportunity if it doesn't exist
        data["opportunity_id"] = self.ensure_opportunity_id(data, context)

        # Update contact transcript field with new summary
        contact_response = self.sharpspring_api_manager.update_contact_transcript(
            data["contact_id"], 
            data["summary"]
        )
        if "error" in contact_response:
            raise APIError(contact_response["error"])
    
    #======================== Role-specific Functions ==========================#
    def meeting_summary(self, transcript: str) -> str:
        prompt = self.configuration.prompt.format(transcript=transcript)
        return self.openai_api_manager.chat(prompt, model=self.OPENAI_SUMMARY_MODEL).choices[0].message.content
    
    def ensure_contact_id(self, data) -> str:
        if not data["contact_id"]: 
            contact_response = self.sharpspring_api_manager.create_contact(
                data["contact"]["name"], 
                data["contact"]["email"], 
                data["contact"]["phone"], 
                data["owner_id"]
            )
            if "error" in contact_response or not contact_response.get("contact_id"):
                raise APIError(contact_response["error"])
            return contact_response["contact_id"]
        return data["contact_id"]
    
    def ensure_transcript_field(self, data) -> str:
        if not data["field_id"]: #This means that we couldn't find the transcript field in the extract step
            field_response = self.sharpspring_api_manager.create_transcript_field()

            if "error" in field_response or not field_response.get("field_id"):
                raise APIError(field_response["error"])
            return field_response["field_id"]
        return data["field_id"]
    
    def ensure_opportunity_id(self, data, context) -> str:
        if not data["opportunity_id"]: #This means that we couldn't find the opportunity in the extract step
            opportunity_response = self.sharpspring_api_manager.create_opportunity(
                context["target"]["email"], 
                context["contact"]["name"], 
                data["contact_id"]
            ) 
            if "error" in opportunity_response or not opportunity_response.get("opportunity_id"):
                raise APIError(opportunity_response["error"])
            return opportunity_response["opportunity_id"]
        return data["opportunity_id"]