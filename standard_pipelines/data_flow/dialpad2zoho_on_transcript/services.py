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

    def find_lead_or_contact(self, person_data: dict) -> tuple[dict, str]:
        """
        Find a lead or contact in Zoho based on email, phone number, or name.
        Uses multiple search methods to minimize duplicate creation.
        
        Args:
            person_data: Dictionary containing available contact information
            
        Returns:
            Tuple of (record, module_name) where record is the Zoho record with 
            normalized field names, and module_name is either "Leads" or "Contacts"
        """
        current_app.logger.info(f"Finding lead or contact for: {person_data}")
        
        # Try to find contact by available identifiers
        record = None
        module_name = None
        
        # STEP 1: Build search criteria from available data
        search_criteria = {}
        
        if person_data.get('email'):
            search_criteria['email'] = person_data['email']
        
        if person_data.get('phonenumber'):
            # Try different phone formats to increase match chances
            phone = person_data['phonenumber']
            
            # Normalize: remove any non-digit characters for comparison
            import re
            digits_only = re.sub(r'\D', '', phone)
            
            # Try different formats - with country code, without, etc.
            if phone.startswith('+'):
                # Without the '+' for searching
                search_criteria['phone'] = phone[1:]
            else:
                search_criteria['phone'] = phone
        
        # Use name as an additional search criterion when available
        if person_data.get('name'):
            name_parts = person_data['name'].split(' ', 1)
            if len(name_parts) > 1:
                search_criteria['first_name'] = name_parts[0]
                search_criteria['last_name'] = name_parts[1]
            else:
                search_criteria['first_name'] = name_parts[0]
        
        # STEP 2: First search in Leads, then in Contacts
        if search_criteria:
            # Search in Leads first
            try:
                current_app.logger.debug(f"Searching for lead with criteria: {search_criteria}")
                # Use match_all=False to perform an OR search across all fields
                lead = self.zoho_api_manager.get_record_by_field("Leads", search_criteria, match_all=False)
                if lead:
                    current_app.logger.info(f"Found lead by combined criteria: {lead.get('id')}")
                    return lead, "Leads"
            except Exception as e:
                current_app.logger.warning(f"Error searching for lead with combined criteria: {e}")
            
            # If no lead found, search in Contacts
            try:
                current_app.logger.debug(f"Searching for contact with criteria: {search_criteria}")
                # Use match_all=False to perform an OR search across all fields
                contact = self.zoho_api_manager.get_record_by_field("Contacts", search_criteria, match_all=False)
                if contact:
                    current_app.logger.info(f"Found contact by combined criteria: {contact.get('id')}")
                    return contact, "Contacts"
            except Exception as e:
                current_app.logger.warning(f"Error searching for contact with combined criteria: {e}")
        
        # STEP 3: If not found, try searching by individual criteria for maximum flexibility
        # Try by email first (most reliable identifier)
        if person_data.get('email'):
            # Search in Leads
            try:
                email_result = self.zoho_api_manager.get_record_by_field("Leads", {'email': person_data['email']})
                if email_result:
                    current_app.logger.info(f"Found lead by email: {email_result.get('id')}")
                    return email_result, "Leads"
            except Exception as e:
                current_app.logger.warning(f"Error searching leads by email: {e}")
            
            # Search in Contacts
            try:
                email_result = self.zoho_api_manager.get_record_by_field("Contacts", {'email': person_data['email']})
                if email_result:
                    current_app.logger.info(f"Found contact by email: {email_result.get('id')}")
                    return email_result, "Contacts"
            except Exception as e:
                current_app.logger.warning(f"Error searching contacts by email: {e}")
        
        # Try by phone number if email didn't work
        if person_data.get('phonenumber'):
            # Try searching for leads by phone
            try:
                # Try with original phone format
                phone_result = self.zoho_api_manager.get_record_by_field("Leads", {'phone': person_data['phonenumber']})
                if phone_result:
                    current_app.logger.info(f"Found lead by phone: {phone_result.get('id')}")
                    return phone_result, "Leads"
                
                # If not found, try with modified formats
                if person_data['phonenumber'].startswith('+'):
                    phone_no_plus = person_data['phonenumber'][1:]
                    phone_result = self.zoho_api_manager.get_record_by_field("Leads", {'phone': phone_no_plus})
                    if phone_result:
                        current_app.logger.info(f"Found lead by phone (no plus): {phone_result.get('id')}")
                        return phone_result, "Leads"
                
                # Try with just digits
                if 'digits_only' in locals():
                    phone_result = self.zoho_api_manager.get_record_by_field("Leads", {'phone': digits_only})
                    if phone_result:
                        current_app.logger.info(f"Found lead by phone (digits only): {phone_result.get('id')}")
                        return phone_result, "Leads"
            except Exception as e:
                current_app.logger.warning(f"Error searching leads by phone: {e}")
            
            # Try searching for contacts by phone
            try:
                # Try with original phone format
                phone_result = self.zoho_api_manager.get_record_by_field("Contacts", {'phone': person_data['phonenumber']})
                if phone_result:
                    current_app.logger.info(f"Found contact by phone: {phone_result.get('id')}")
                    return phone_result, "Contacts"
                
                # If not found, try with modified formats
                if person_data['phonenumber'].startswith('+'):
                    phone_no_plus = person_data['phonenumber'][1:]
                    phone_result = self.zoho_api_manager.get_record_by_field("Contacts", {'phone': phone_no_plus})
                    if phone_result:
                        current_app.logger.info(f"Found contact by phone (no plus): {phone_result.get('id')}")
                        return phone_result, "Contacts"
                
                # Try with just digits
                if 'digits_only' in locals():
                    phone_result = self.zoho_api_manager.get_record_by_field("Contacts", {'phone': digits_only})
                    if phone_result:
                        current_app.logger.info(f"Found contact by phone (digits only): {phone_result.get('id')}")
                        return phone_result, "Contacts"
            except Exception as e:
                current_app.logger.warning(f"Error searching contacts by phone: {e}")
        
        # STEP 4: Search by name as a last resort
        if person_data.get('name'):
            name_parts = person_data['name'].split(' ', 1)
            
            # Search in Leads by name
            try:
                if len(name_parts) > 1:
                    # Try to find by first name and last name
                    name_result = self.zoho_api_manager.get_record_by_field(
                        "Leads", 
                        {'first_name': name_parts[0], 'last_name': name_parts[1]},
                        match_all=True
                    )
                    if name_result:
                        current_app.logger.info(f"Found lead by full name: {name_result.get('id')}")
                        return name_result, "Leads"
                else:
                    # Try by first name only
                    name_result = self.zoho_api_manager.get_record_by_field("Leads", {'first_name': name_parts[0]})
                    if name_result:
                        current_app.logger.info(f"Found lead by first name: {name_result.get('id')}")
                        return name_result, "Leads"
            except Exception as e:
                current_app.logger.warning(f"Error searching leads by name: {e}")
            
            # Search in Contacts by name
            try:
                if len(name_parts) > 1:
                    # Try to find by first name and last name
                    name_result = self.zoho_api_manager.get_record_by_field(
                        "Contacts", 
                        {'first_name': name_parts[0], 'last_name': name_parts[1]},
                        match_all=True
                    )
                    if name_result:
                        current_app.logger.info(f"Found contact by full name: {name_result.get('id')}")
                        return name_result, "Contacts"
                else:
                    # Try by first name only
                    name_result = self.zoho_api_manager.get_record_by_field("Contacts", {'first_name': name_parts[0]})
                    if name_result:
                        current_app.logger.info(f"Found contact by first name: {name_result.get('id')}")
                        return name_result, "Contacts"
            except Exception as e:
                current_app.logger.warning(f"Error searching contacts by name: {e}")
        
        # STEP 5: If no existing lead or contact found, create a new contact
        current_app.logger.info(f"No lead or contact found after extensive search, creating new contact")
        
        # Prepare contact data using Zoho's expected field names
        contact_data = {}
        
        # Split name into first and last name
        if person_data.get('name'):
            name_parts = person_data['name'].split(' ', 1)
            contact_data["First_Name"] = name_parts[0]
            contact_data["Last_Name"] = name_parts[1] if len(name_parts) > 1 else ""
        else:
            # Use email prefix as first name if name not available
            if person_data.get('email'):
                contact_data["First_Name"] = person_data['email'].split('@')[0]
            else:
                contact_data["First_Name"] = "Unknown"
            contact_data["Last_Name"] = ""
        
        # Add email if available
        if person_data.get('email'):
            contact_data["Email"] = person_data['email']
        
        # Add phone if available
        if person_data.get('phonenumber'):
            contact_data["Phone"] = person_data['phonenumber']
        
        try:
            contact = self.zoho_api_manager.create_record("Contacts", contact_data)
            current_app.logger.info(f"Created new contact: {contact}")
            
            # Make sure the contact object has properly normalized field names
            normalized_contact = {}
            
            # Copy the original contact data
            if isinstance(contact, dict):
                normalized_contact = contact.copy()
            else:
                # If contact is not a dict, start with the ID at minimum
                normalized_contact = {"id": str(contact)}
            
            # Ensure First_Name and Last_Name fields exist
            if "First_Name" not in normalized_contact and contact_data.get("First_Name"):
                normalized_contact["First_Name"] = contact_data["First_Name"]
            
            if "Last_Name" not in normalized_contact and contact_data.get("Last_Name"):
                normalized_contact["Last_Name"] = contact_data["Last_Name"]
            
            # Ensure Email field exists
            if "Email" not in normalized_contact and contact_data.get("Email"):
                normalized_contact["Email"] = contact_data["Email"]
            
            # Ensure Phone field exists  
            if "Phone" not in normalized_contact and contact_data.get("Phone"):
                normalized_contact["Phone"] = contact_data["Phone"]
            
            current_app.logger.debug(f"Normalized contact data: {normalized_contact}")
            return normalized_contact, "Contacts"
            
        except APIError as e:
            current_app.logger.error(f"Failed to create contact: {str(e)}")
            raise


    def _extract_contact_name(self, contact: dict) -> str:
        """
        Helper method to extract the contact name from a contact object
        using multiple possible field name formats.
        
        Args:
            contact: Contact dictionary
            
        Returns:
            Extracted contact name or "Unknown Contact" if not found
        """
        # Log the entire contact object to debug field name issues
        current_app.logger.debug(f"Extracting name from contact: {json.dumps(contact, indent=2)}")
        
        # Try different field name formats that might exist in the contact object
        possible_first_name_fields = ['First_Name', 'first_name', 'firstName', 'firstname', 'FirstName']
        possible_last_name_fields = ['Last_Name', 'last_name', 'lastName', 'lastname', 'LastName']
        
        # Extract first name
        first_name = ''
        for field in possible_first_name_fields:
            if field in contact:
                first_name = contact[field]
                current_app.logger.debug(f"Found first name in field {field}: {first_name}")
                break
                
        # Extract last name
        last_name = ''
        for field in possible_last_name_fields:
            if field in contact:
                last_name = contact[field]
                current_app.logger.debug(f"Found last name in field {field}: {last_name}")
                break
        
        # Build full name if we have components
        contact_name = "Unknown Contact"
        if first_name or last_name:
            contact_name = f"{first_name} {last_name}".strip()
            current_app.logger.info(f"Using contact name: {contact_name}")
        
        # If we still don't have a name, try email or other identifiers
        if not contact_name or contact_name == "Unknown Contact":
            for email_field in ['Email', 'email', 'emailAddress', 'email_address']:
                if email_field in contact and contact[email_field]:
                    contact_name = contact[email_field]
                    current_app.logger.info(f"Using email as contact name: {contact_name}")
                    break
            
            # Last resort - check for phone
            if not contact_name or contact_name == "Unknown Contact":
                for phone_field in ['Phone', 'phone', 'phoneNumber', 'phone_number']:
                    if phone_field in contact and contact[phone_field]:
                        contact_name = contact[phone_field]
                        current_app.logger.info(f"Using phone as contact name: {contact_name}")
                        break
        
        return contact_name

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
        
        # Find or create lead/contact in Zoho
        try:
            record, module_name = self.find_lead_or_contact(guest)
            current_app.logger.info(f"Found/created {module_name} record: {json.dumps(record, indent=4)}")
        except Exception as e:
            current_app.logger.error(f"Error processing lead/contact: {str(e)}")
            raise
        
        # Ensure record has an ID property
        record_id = None
        if isinstance(record, dict) and 'id' in record:
            record_id = record['id']
        elif hasattr(record, 'get') and callable(getattr(record, 'get')):
            record_id = record.get('id')
        else:
            # Last resort - use the string representation
            record_id = str(record)
            current_app.logger.warning(f"Using record string representation as ID: {record_id}")
        
        # Enrich transcript with record information
        enriched_transcript = self.enrich_transcript(transcript, record)
        
        # Perform BANT analysis
        bant_analysis = self.perform_bant_analysis(enriched_transcript)
        
        # Create notes data
        transcript_note_data = {
            "Note_Title": f"Call Transcript - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "Note_Content": enriched_transcript,
            "Parent_Id": {"id": record_id, "module": module_name}
        }
        
        bant_note_data = {
            "Note_Title": f"BANT Analysis - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "Note_Content": bant_analysis,
            "Parent_Id": {"id": record_id, "module": module_name}
        }
        
        return {
            "record": record,
            "module_name": module_name,
            "transcript_note": transcript_note_data,
            "bant_note": bant_note_data
        }

    def load(self, data: dict, context: t.Optional[dict] = None) -> dict:
        """
        Load the transformed data into Zoho CRM.
        """
        record = data["record"]
        module_name = data["module_name"]
        transcript_note_data = data["transcript_note"]
        bant_note_data = data["bant_note"]
        
        results = {
            "record_id": record.get('id'),
            "module_name": module_name
        }
        
        # Create transcript note
        try:
            transcript_note = self.zoho_api_manager.create_note(
                transcript_note_data, 
                record.get('id'), 
                module_name
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
                record.get('id'), 
                module_name
            )
            results["bant_note_id"] = bant_note.get('id', '')
            current_app.logger.info(f"Created BANT analysis note with ID: {bant_note.get('id', '')}")
        except Exception as e:
            current_app.logger.error(f"Error creating BANT analysis note: {str(e)}")
            results["bant_note_error"] = str(e)
        
        return results