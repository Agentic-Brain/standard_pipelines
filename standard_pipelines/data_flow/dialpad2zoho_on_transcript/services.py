import datetime
import json
import typing as t
from functools import cached_property
from typing import Optional, Any, List, Dict, Union

from flask import current_app

from ...api.dialpad.models import DialpadCredentials
from ...api.zoho.models import ZohoCredentials
from ...api.dialpad.services import DialpadAPIManager
from ...api.zoho.services import ZohoAPIManager
from ...api.openai.services import OpenAIAPIManager
from ...api.openai.models import OpenAICredentials
from ..services import BaseDataFlow
from ..exceptions import InvalidWebhookError
from .models import Dialpad2ZohoOnTranscriptConfiguration
from standard_pipelines.data_flow.exceptions import APIError


class Dialpad2ZohoOnTranscript(BaseDataFlow[Dialpad2ZohoOnTranscriptConfiguration]):
    """
    Data flow to process Dialpad transcripts and create/update Zoho CRM records.
    """
    
    OPENAI_MODEL = "gpt-4o"
    
    @classmethod
    def data_flow_name(cls) -> str:
        return "dialpad2zoho_on_transcript"

    @cached_property
    def zoho_api_manager(self) -> ZohoAPIManager:
        credentials: Optional[ZohoCredentials] = ZohoCredentials.query.filter_by(client_id=self.client_id).first()
        if credentials is None:
            raise ValueError("No Zoho credentials found for client")
        return ZohoAPIManager(credentials)

    @cached_property
    def dialpad_api_manager(self) -> DialpadAPIManager:
        credentials = DialpadCredentials.query.filter_by(client_id=self.client_id).first()
        if not credentials:
            raise ValueError(f"No Dialpad credentials found for client {self.client_id}")
        
        dialpad_config = {
            "api_key": credentials.dialpad_api_key,
        }
        return DialpadAPIManager(dialpad_config)
    
    @cached_property
    def openai_api_manager(self) -> OpenAIAPIManager:
        credentials = OpenAICredentials.query.filter_by(client_id=self.client_id).first()
        if not credentials:
            raise ValueError(f"No OpenAI credentials found for client {self.client_id}")
        
        openai_config = {
            "api_key": credentials.openai_api_key
        }
        return OpenAIAPIManager(openai_config)

    def context_from_webhook_data(self, webhook_data: t.Any) -> t.Optional[dict]:
        """
        Extract context from webhook data.
        """
        if not isinstance(webhook_data, dict):
            raise InvalidWebhookError(f"Expected 'webhook_data' to be a dict, got type {type(webhook_data)}. Value: {webhook_data}")
        
        if webhook_data.get("state") != "hangup":
            raise InvalidWebhookError('Webhook does not represent a call hangup')
        
        call_id = webhook_data.get("call_id")
        if not isinstance(call_id, int):
            raise InvalidWebhookError("Invalid call ID")
        
        return {
            "call_id": call_id
        }

    def extract(self, context: t.Optional[dict] = None) -> dict:
        """
        Extract transcript and participant data from Dialpad API.
        """
        if not context:
            raise ValueError("No call ID provided")
        
        call_id = context["call_id"]
        transcript_dict: dict[str, Any] = self.dialpad_api_manager.get_transcript(call_id)
        transcript = transcript_dict["transcript"]
        participants = transcript_dict["participants"]

        # Assuming participants contains host and guest
        return {
            "transcript": transcript,
            "guest": participants.get("guest"),
            "host": participants.get("host"),
        }

    def find_or_create_contact(self, person_data: dict) -> dict:
        """
        Find or create a contact in Zoho based on email, phone number, or name.
        
        Args:
            person_data: Dictionary containing available contact information
            
        Returns:
            Zoho contact record
        """
        current_app.logger.info(f"Finding or creating contact for: {person_data}")
        
        # Try to find contact by available identifiers
        contact = None
        search_criteria = {}
        
        # Build search criteria from available data
        if person_data.get('email'):
            search_criteria['email'] = person_data['email']
        
        if person_data.get('phonenumber'):
            phone = person_data['phonenumber']
            # Normalize phone number format if needed
            if phone.startswith('+'):
                # Remove the '+' for searching
                phone = phone[1:]
            search_criteria['phone'] = phone
        
        # Use name as a last resort if available
        if person_data.get('name') and not (search_criteria.get('email') or search_criteria.get('phone')):
            # Since name can be ambiguous, only use it if no other identifiers are available
            name_parts = person_data['name'].split(' ', 1)
            if len(name_parts) > 1:
                search_criteria['first_name'] = name_parts[0]
                search_criteria['last_name'] = name_parts[1]
            else:
                search_criteria['first_name'] = name_parts[0]
        
        # Try to find the contact with all available criteria at once (OR search)
        if search_criteria:
            try:
                current_app.logger.debug(f"Searching for contact with criteria: {search_criteria}")
                # Use match_all=False to perform an OR search across all fields
                contact = self.zoho_api_manager.get_record_by_field("Contacts", search_criteria, match_all=False)
                if contact:
                    current_app.logger.info(f"Found contact: {contact.get('id')}")
            except Exception as e:
                current_app.logger.warning(f"Error searching for contact: {e}")
        
        # Create new contact if not found
        if not contact:
            current_app.logger.info(f"Contact not found, creating new contact")
            
            # Prepare contact data
            if person_data.get('name'):
                name_parts = person_data['name'].split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""
            else:
                # Use email prefix as first name if name not available
                if person_data.get('email'):
                    first_name = person_data['email'].split('@')[0]
                else:
                    first_name = "Unknown"
                last_name = ""
            
            contact_data = {
                "First_Name": first_name,
                "Last_Name": last_name
            }
            
            # Add email if available
            if person_data.get('email'):
                contact_data["Email"] = person_data['email']
            
            # Add phone if available
            if person_data.get('phonenumber'):
                contact_data["Phone"] = person_data['phonenumber']
            
            try:
                contact = self.zoho_api_manager.create_record("Contacts", contact_data)
                current_app.logger.info(f"Created new contact: {contact}")
            except APIError as e:
                current_app.logger.error(f"Failed to create contact: {str(e)}")
                raise
        
        return contact

    def find_or_create_deal(self, contact: dict, host_user: dict = None) -> dict:
        """
        Find or create a deal associated with the contact.
        
        Args:
            contact: Zoho contact record
            host_user: Zoho user record for the host
            
        Returns:
            Zoho deal record
        """
        current_app.logger.info(f"Finding or creating deal for contact ID: {contact.get('id')}")
        
        deal = None
        contact_id = contact.get('id')
        
        if contact_id:
            try:
                # Try to find existing deals associated with this contact
                deals = self.zoho_api_manager.search_by_lookup_field("Deals", "Contact_Name", contact_id)
                
                if deals and len(deals) > 0:
                    deal = deals[0]
                    current_app.logger.info(f"Found existing deal: {deal.get('id')}")
            except APIError as e:
                current_app.logger.warning(f"Error searching for deals: {str(e)}")
        
        # Create new deal if not found
        if not deal:
            current_app.logger.info("No deal found, creating new deal")
            
            # Get contact's full name for deal name
            contact_first_name = contact.get('First_Name', '')
            contact_last_name = contact.get('Last_Name', '')
            contact_name = f"{contact_first_name} {contact_last_name}".strip()
            if not contact_name:
                contact_name = contact.get('Email', 'Unknown Contact')
            
            if not self.configuration.initial_deal_stage_id or type(self.configuration.initial_deal_stage_id) != str:
                raise ValueError("No initial deal stage ID configured")
            
            # Prepare deal data
            deal_data = {
                "Deal_Name": f"Deal for {contact_name}",
                "Stage": self.configuration.initial_deal_stage_id,  # Assuming this is configured
                "Contact_Name": {"id": contact_id}  # Link to contact
            }
            
            # Add owner if host user is available
            if host_user and host_user.get('id'):
                deal_data["Owner"] = {"id": host_user.get('id')}
            
            try:
                deal = self.zoho_api_manager.create_record("Deals", deal_data)
                current_app.logger.info(f"Created new deal: {deal}")
            except APIError as e:
                current_app.logger.error(f"Failed to create deal: {str(e)}")
                raise
        
        return deal

    def enrich_transcript(self, transcript: str, contact: dict) -> str:
        """
        Replace identifiers in transcript with user's full name or email.
        
        Args:
            transcript: Original transcript
            contact: Zoho contact record
            
        Returns:
            Enriched transcript
        """
        enriched_transcript = transcript
        
        # Get contact information for replacement
        contact_first_name = contact.get('First_Name', '')
        contact_last_name = contact.get('Last_Name', '')
        full_name = f"{contact_first_name} {contact_last_name}".strip()
        email = contact.get('Email', '')
        phone = contact.get('Phone', '')
        
        # Determine what identifier to use for replacement
        identifier = full_name if full_name else (email if email else phone)
        
        # Replace phone number in transcript if it appears
        if phone and phone in transcript:
            enriched_transcript = enriched_transcript.replace(phone, identifier)
        
        # Replace email in transcript if it appears
        if email and email in transcript:
            enriched_transcript = enriched_transcript.replace(email, identifier)
        
        return enriched_transcript

    def perform_bant_analysis(self, transcript: str) -> str:
        """
        Perform BANT analysis on the transcript using OpenAI API.
        
        Args:
            transcript: Call transcript
            
        Returns:
            BANT analysis as a string
        """
        prompt = f"""
        Please analyze the following sales call transcript using the BANT framework:
        
        Budget: Does the prospect have the budget for our product/service?
        Authority: Is the person a decision-maker or do they have influence?
        Need: What specific problems or needs does the prospect have?
        Timeline: When is the prospect planning to make a decision or implement a solution?
        
        Please provide a detailed analysis for each component based only on what is explicitly mentioned in the transcript.
        
        Transcript:
        {transcript}
        
        Format your response as follows:
        
        ## BANT Analysis
        
        ### Budget
        [Analysis of budget aspects]
        
        ### Authority
        [Analysis of decision-making authority]
        
        ### Need
        [Analysis of prospect's needs and pain points]
        
        ### Timeline
        [Analysis of prospect's implementation timeline]
        
        ### Summary
        [Brief summary of BANT qualification status and next steps]
        """
        
        try:
            response = self.openai_api_manager.chat(prompt, model=self.OPENAI_MODEL)
            analysis = response.choices[0].message.content
            current_app.logger.info("Successfully performed BANT analysis")
            return analysis
        except Exception as e:
            current_app.logger.error(f"Error performing BANT analysis: {str(e)}")
            return "Error performing BANT analysis. Please review the transcript manually."

    def transform(self, data: dict, context: t.Optional[dict] = None) -> dict:
        """
        Transform the extracted data into Zoho format.
        """
        transcript = data["transcript"]
        guest = data["guest"]
        host = data["host"]
        
        current_app.logger.debug(f"Transcript: {transcript}")
        current_app.logger.debug(f"Guest: {guest}")
        current_app.logger.debug(f"Host: {host}")
        
        # Find or create host user in Zoho
        host_user = None
        if host and host.get('email'):
            try:
                host_user = self.zoho_api_manager.get_user_by_email(host['email'])
                current_app.logger.info(f"Found host user: {host_user.get('id')}")
            except APIError as e:
                current_app.logger.warning(f"Host user not found: {e}")
        
        # Find or create guest contact in Zoho
        try:
            contact = self.find_or_create_contact(guest)
            current_app.logger.info(f"Contact: {json.dumps(contact, indent=4)}")
        except Exception as e:
            current_app.logger.error(f"Error processing contact: {str(e)}")
            raise
        
        # Find or create deal
        try:
            deal = self.find_or_create_deal(contact, host_user)
            current_app.logger.info(f"Deal: {json.dumps(deal, indent=4)}")
        except Exception as e:
            current_app.logger.error(f"Error processing deal: {str(e)}")
            raise
        
        # Enrich transcript with contact information
        enriched_transcript = self.enrich_transcript(transcript, contact)
        
        # Perform BANT analysis
        bant_analysis = self.perform_bant_analysis(enriched_transcript)
        
        # Create notes data
        transcript_note_data = {
            "Note_Title": f"Call Transcript - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "Note_Content": enriched_transcript,
            "Parent_Id": {"id": deal.get('id'), "module": "Deals"}
        }
        
        bant_note_data = {
            "Note_Title": f"BANT Analysis - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "Note_Content": bant_analysis,
            "Parent_Id": {"id": deal.get('id'), "module": "Deals"}
        }
        
        return {
            "contact": contact,
            "deal": deal,
            "transcript_note": transcript_note_data,
            "bant_note": bant_note_data
        }

    def load(self, data: dict, context: t.Optional[dict] = None) -> dict:
        """
        Load the transformed data into Zoho CRM.
        """
        contact = data["contact"]
        deal = data["deal"]
        transcript_note_data = data["transcript_note"]
        bant_note_data = data["bant_note"]
        
        results = {
            "contact_id": contact.get('id'),
            "deal_id": deal.get('id')
        }
        
        # Create transcript note
        try:
            transcript_note = self.zoho_api_manager.create_note(
                transcript_note_data, 
                deal.get('id'), 
                "Deals"
            )
            results["transcript_note_id"] = transcript_note.get('id', '')
            current_app.logger.info(f"Created transcript note with ID: {transcript_note.get('id', '')}")
        except Exception as e:
            current_app.logger.error(f"Error creating transcript note: {str(e)}")
            results["transcript_note_error"] = str(e)
        
        # Create BANT analysis note
        try:
            bant_note = self.zoho_api_manager.create_note(
                bant_note_data, 
                deal.get('id'), 
                "Deals"
            )
            results["bant_note_id"] = bant_note.get('id', '')
            current_app.logger.info(f"Created BANT analysis note with ID: {bant_note.get('id', '')}")
        except Exception as e:
            current_app.logger.error(f"Error creating BANT analysis note: {str(e)}")
            results["bant_note_error"] = str(e)
        
        return results