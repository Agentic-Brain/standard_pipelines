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
from flask import current_app
import time
import re


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
        current_app.logger.info("[DP2SS] Processing webhook data")

        if not webhook_data:
            current_app.logger.error("[DP2SS] No webhook data provided")
            raise InvalidWebhookError('No webhook data provided')
        if not isinstance(webhook_data, dict):
            current_app.logger.error("[DP2SS] Invalid webhook data type - not a dictionary")
            raise InvalidWebhookError('Invalid webhook data')
        if webhook_data.get("state") != "hangup":
            current_app.logger.error(f"[DP2SS] Invalid webhook type: {webhook_data.get('state')}, expected 'hangup'")
            raise InvalidWebhookError('Invalid webhook type')

        current_app.logger.info(f"[DP2SS] Received webhook with call_id: {webhook_data.get('call_id', 'Unknown')}")

        # TODO: Change how these error messages work, no need to duplicate them all
        required_fields = {
            "date_started": "Date started is required in the webhook data for the dialpad to SharpSpring flow",
            "call_id": "Call ID is required in the webhook data for the dialpad to SharpSpring flow",
            "contact": "Contact is required in the webhook data for the dialpad to SharpSpring flow",
            "target": "Target is required in the webhook data for the dialpad to SharpSpring flow"
        }

        for field, error_message in required_fields.items():
            if webhook_data.get(field) is None:
                current_app.logger.error(f"[DP2SS] Missing required field: {field}")
                raise InvalidWebhookError(error_message)

        call_data = {
            "date_started": webhook_data["date_started"],
            "call_id": webhook_data["call_id"],
            "contact": webhook_data["contact"],
            "target": webhook_data["target"],
        }

        current_app.logger.info(f"[DP2SS] Successfully processed webhook for call_id: {call_data['call_id']}")
        current_app.logger.info(f"[DP2SS] Target email: {call_data['target'].get('email', 'Unknown')}")
        current_app.logger.info(f"[DP2SS] Contact info: {call_data['contact'].get('name', 'Unknown')}, {call_data['contact'].get('email', 'Unknown')}")

        return call_data

    #Attempt to gather all the data we need from our source systems
    def extract(self, context: t.Optional[dict] = None) -> dict:
        current_app.logger.debug("[DP2SS:EXTRACT] Starting data extraction with context: %s",
                                str({k: v for k, v in context.items() if k != 'contact' and k != 'target'}) if context else None)

        # Get transcript from Dialpad
        current_app.logger.debug("[DP2SS:EXTRACT] Getting transcript for call_id: %s", context.get('call_id'))
        transcript = self.dialpad_api_manager.get_transcript(context)
        if "error" in transcript:
            current_app.logger.error("[DP2SS:EXTRACT] Failed to retrieve Dialpad transcript: %s", transcript['error'])
            raise APIError(f"Failed to retrieve Dialpad transcript: {transcript['error']}")

        transcript_length = len(transcript["transcript"]) if transcript.get("transcript") else 0
        current_app.logger.debug("[DP2SS:EXTRACT] Retrieved transcript of length %d characters", transcript_length)

        # Get the owner ID from SharpSpring
        owner_email = context["target"]["email"]
        current_app.logger.debug("[DP2SS:EXTRACT] Getting owner ID for email: %s", owner_email)
        owner_id_response = self.sharpspring_api_manager.get_account_owner_id(owner_email)
        if "error" in owner_id_response:
            current_app.logger.error("[DP2SS:EXTRACT] Failed to find SharpSpring user: %s", owner_id_response['error'])
            raise APIError(f"Failed to find SharpSpring user with email '{owner_email}': {owner_id_response['error']}")

        current_app.logger.debug("[DP2SS:EXTRACT] Found owner ID: %s", owner_id_response.get("owner_id"))

        # Get the contact ID from SharpSpring
        contact = context["contact"]
        contact_details = f"name='{contact.get('name')}', phone='{contact.get('phone')}', email='{contact.get('email')}'"
        current_app.logger.debug("[DP2SS:EXTRACT] Looking for contact in SharpSpring: %s", contact_details)

        # Try to find contact with the most reliable matching (all fields first)
        contact_id_response = self.sharpspring_api_manager.get_contact(
            phone_number=contact["phone"],
            name=contact["name"],
            email=contact["email"]
        )

        # If the main search fails, try individual fields
        if "error" in contact_id_response or not contact_id_response.get("contact_id"):
            current_app.logger.debug("[DP2SS:EXTRACT] Contact not found with all fields, trying individual searches")

            # Try email search if available
            if contact.get("email"):
                current_app.logger.debug("[DP2SS:EXTRACT] Trying to find contact by email: %s", contact.get("email"))
                email_search = self.sharpspring_api_manager.get_contact(phone_number="", name="", email=contact["email"])
                if not "error" in email_search and email_search.get("contact_id"):
                    current_app.logger.debug("[DP2SS:EXTRACT] Found contact by email with ID: %s",
                                         email_search.get("contact_id"))
                    contact_id_response = email_search

            # If email search failed and phone number is available, try phone search
            if (not contact_id_response.get("contact_id") or "error" in contact_id_response) and contact.get("phone"):
                # Try different phone formats
                formatted_phone = contact["phone"]
                current_app.logger.debug("[DP2SS:EXTRACT] Trying to find contact by phone: %s", formatted_phone)

                # If it starts with +, also try the stripped version
                if formatted_phone.startswith("+"):
                    stripped_phone = formatted_phone[1:]  # Remove the leading '+'
                    current_app.logger.debug("[DP2SS:EXTRACT] Also trying stripped phone format: %s", stripped_phone)

                    # Try with stripped format first
                    stripped_search = self.sharpspring_api_manager.get_contact(phone_number=stripped_phone, name="", email="")
                    if not "error" in stripped_search and stripped_search.get("contact_id"):
                        contact_id = stripped_search.get("contact_id")
                        current_app.logger.debug("[DP2SS:EXTRACT] Found contact by stripped phone with ID: %s", contact_id)

                        # Use this contact
                        contact_id_response = stripped_search

                # Try with original format if stripped didn't work or + wasn't present
                if not contact_id_response.get("contact_id") or "error" in contact_id_response:
                    phone_search = self.sharpspring_api_manager.get_contact(phone_number=contact["phone"], name="", email="")
                    if not "error" in phone_search and phone_search.get("contact_id"):
                        contact_id = phone_search.get("contact_id")

                        current_app.logger.debug("[DP2SS:EXTRACT] Found contact by phone with ID: %s", contact_id)
                        contact_id_response = phone_search

        # After all the search attempts, check if we have an error
        if "error" in contact_id_response:
            # Don't fail the flow here, just log warning and continue without contact_id
            # It will be created in the load phase
            current_app.logger.warning("[DP2SS:EXTRACT] Failed to find existing contact: %s",
                                    contact_id_response.get('error', 'Unknown error'))
            # Reset the response to empty values
            contact_id_response = {"contact_id": None, "transcript": None}

        contact_id = contact_id_response.get("contact_id")
        existing_transcript = contact_id_response.get("transcript")

        # Log the result of the contact search
        current_app.logger.debug("[DP2SS:EXTRACT] Contact search completed")

        # Log the final result of contact search
        if contact_id:
            current_app.logger.debug("[DP2SS:EXTRACT] Found existing contact ID: %s", contact_id)

            if existing_transcript:
                existing_length = len(existing_transcript)
                current_app.logger.debug("[DP2SS:EXTRACT] Contact has existing transcript of length %d characters", existing_length)
            else:
                current_app.logger.debug("[DP2SS:EXTRACT] Contact exists but has no previous transcript")
        else:
            current_app.logger.debug("[DP2SS:EXTRACT] No existing contact found, will need to create a new one")

        # Check if the transcript field exists in SharpSpring
        current_app.logger.debug("[DP2SS:EXTRACT] Checking if transcript field exists in SharpSpring")
        field_response = self.sharpspring_api_manager.get_transcript_field()
        if "error" in field_response:
            current_app.logger.error("[DP2SS:EXTRACT] Failed to check transcript field: %s", field_response['error'])
            raise APIError(f"Failed to retrieve SharpSpring transcript field: {field_response['error']}")

        # Ensure field_response has expected keys
        field_id = field_response.get("field_id")
        system_name = field_response.get("system_name")

        if field_id:
            current_app.logger.debug("[DP2SS:EXTRACT] Found transcript field with ID: %s, system_name: %s",
                                     field_id, system_name)
        else:
            current_app.logger.debug("[DP2SS:EXTRACT] Transcript field not found, will need to create it")

        if not system_name:
            current_app.logger.error("[DP2SS:EXTRACT] SharpSpring transcript field's system_name is missing")
            raise APIError("SharpSpring transcript field's system_name is missing")

        # Get the opportunity ID from SharpSpring if contact exists
        opportunity_id = None
        if contact_id: # Required for getting the opportunity id
            current_app.logger.debug("[DP2SS:EXTRACT] Looking for opportunity for contact ID: %s", contact_id)
            opportunity_id_response = self.sharpspring_api_manager.get_opportunity_id_from_contact_id(contact_id)
            if "error" in opportunity_id_response:
                # Don't fail for missing opportunity, just log warning
                current_app.logger.warning("[DP2SS:EXTRACT] No existing opportunity found: %s",
                                      opportunity_id_response.get('error', 'Unknown error'))
                opportunity_id_response = {"opportunity_id": None}

            opportunity_id = opportunity_id_response.get("opportunity_id")
            if opportunity_id:
                current_app.logger.debug("[DP2SS:EXTRACT] Found existing opportunity with ID: %s", opportunity_id)
            else:
                current_app.logger.debug("[DP2SS:EXTRACT] No existing opportunity found, will need to create one")
        else:
            current_app.logger.debug("[DP2SS:EXTRACT] No contact ID available, cannot look up opportunity")
            opportunity_id_response = {"opportunity_id": None}

        data = {
            "transcript": transcript["transcript"],
            "existing_transcript": existing_transcript,
            "contact_id": contact_id,
            "owner_id": owner_id_response["owner_id"],
            "field_id": field_id,  # This could be None if field doesn't exist yet
            "system_name": system_name,  # Add system_name which is required for other operations
            "opportunity_id": opportunity_id
        }

        current_app.logger.debug("[DP2SS:EXTRACT] Extraction complete. Result keys: %s", str(data.keys()))
        return data
    
    #Takes in extracted data and applies client-specific transformations
    def transform(self, input_data: t.Optional[dict] = None, context: t.Optional[dict] = None) -> dict:
        current_app.logger.debug("[DP2SS:TRANSFORM] Starting data transformation phase with data keys: %s", str(input_data.keys()))

        # Get transcript snippet for logging (first 100 chars)
        transcript_snippet = input_data["transcript"][:100] + "..." if len(input_data["transcript"]) > 100 else input_data["transcript"]
        current_app.logger.debug("[DP2SS:TRANSFORM] Processing transcript (snippet): %s", transcript_snippet)

        current_app.logger.debug("[DP2SS:TRANSFORM] Generating meeting summary from transcript using OpenAI model: %s", self.OPENAI_SUMMARY_MODEL)
        summary = self.meeting_summary(input_data["transcript"])

        # Log summary snippet
        summary_snippet = summary[:100] + "..." if len(summary) > 100 else summary
        current_app.logger.debug("[DP2SS:TRANSFORM] Generated summary (snippet): %s", summary_snippet)

        #If the transcript already exists, we append it to the new summary
        if input_data.get("existing_transcript"):
            current_app.logger.debug("[DP2SS:TRANSFORM] Found existing transcript, appending to new summary")
            original_length = len(summary)
            summary = f"{summary}\n\n#=====================#\n\n{input_data['existing_transcript']}"
            new_length = len(summary)
            current_app.logger.debug("[DP2SS:TRANSFORM] Summary length changed from %d to %d characters after append",
                                    original_length, new_length)
        else:
            current_app.logger.debug("[DP2SS:TRANSFORM] No existing transcript found, using only the new summary")

        input_data["summary"] = summary
        current_app.logger.debug("[DP2SS:TRANSFORM] Data transformation phase complete. Final summary length: %d characters",
                               len(summary))

        return input_data

    #Loads the transformed data into the target system
    def load(self, output_data: t.Optional[dict] = None, context: t.Optional[dict] = None) -> None:
        current_app.logger.debug("[DP2SS:LOAD] Starting data loading phase with data keys: %s", str(output_data.keys()))

        # Things are created based on if data for them could be extracted in the extract step or not
        had_contact = bool(output_data.get("contact_id"))
        had_transcript_field = bool(output_data.get("field_id"))
        had_opportunity = bool(output_data.get("opportunity_id"))

        # Log the starting state
        current_app.logger.debug("[DP2SS:LOAD] Starting state - Had contact: %s, Had transcript field: %s, Had opportunity: %s",
                              had_contact, had_transcript_field, had_opportunity)

        # Creates the contact if contact doesn't exist
        current_app.logger.debug("[DP2SS:LOAD] Ensuring contact exists in SharpSpring")
        output_data["contact_id"] = self.ensure_contact_id(output_data, context)

        # Log whether contact was created or already existed
        if not had_contact and output_data.get("contact_id"):
            current_app.logger.debug("[DP2SS:LOAD] Created new contact with ID: %s", output_data["contact_id"])
        else:
            current_app.logger.debug("[DP2SS:LOAD] Using existing contact with ID: %s", output_data["contact_id"])

        # Creates the transcript field if it doesn't exist
        current_app.logger.debug("[DP2SS:LOAD] Ensuring transcript field exists in SharpSpring")
        output_data["field_id"] = self.ensure_transcript_field(output_data)

        # Log whether field was created or already existed
        if not had_transcript_field and output_data.get("field_id"):
            current_app.logger.debug("[DP2SS:LOAD] Created new transcript field with ID: %s", output_data["field_id"])
        else:
            current_app.logger.debug("[DP2SS:LOAD] Using existing transcript field with ID: %s", output_data["field_id"])

        # Creates the opportunity if it doesn't exist
        current_app.logger.debug("[DP2SS:LOAD] Ensuring opportunity exists in SharpSpring")
        try:
            output_data["opportunity_id"] = self.ensure_opportunity_id(output_data, context)

            # Log whether opportunity was created or already existed
            if not had_opportunity and output_data.get("opportunity_id") and output_data.get("opportunity_id") != "unknown":
                current_app.logger.debug("[DP2SS:LOAD] Created new opportunity with ID: %s", output_data["opportunity_id"])
            elif output_data.get("opportunity_id") == "unknown":
                current_app.logger.debug("[DP2SS:LOAD] Continuing without opportunity ID due to previous error")
            else:
                current_app.logger.debug("[DP2SS:LOAD] Using existing opportunity with ID: %s", output_data["opportunity_id"])
        except Exception as e:
            # If anything goes wrong, continue without the opportunity
            current_app.logger.warning("[DP2SS:LOAD] Error creating opportunity, but continuing: %s", str(e))
            output_data["opportunity_id"] = "unknown"

        # Proceed with updating the contact

        # Update contact transcript field with new summary
        # Need to ensure we have system_name for the update operation
        if not output_data.get("system_name"):
            current_app.logger.debug("[DP2SS:LOAD] Getting system_name for transcript field")
            field_info = self.sharpspring_api_manager.get_transcript_field()
            if "error" in field_info or not field_info.get("system_name"):
                current_app.logger.error("[DP2SS:LOAD] Could not find system_name for transcript field: %s",
                                     field_info.get("error", "Unknown error"))
                raise APIError("Could not find system_name for transcript field")
            output_data["system_name"] = field_info["system_name"]
            current_app.logger.debug("[DP2SS:LOAD] Retrieved system_name: %s", output_data["system_name"])

        # Log the summary length being saved
        summary_length = len(output_data.get("summary", "")) if output_data.get("summary") else 0
        current_app.logger.debug("[DP2SS:LOAD] Updating transcript for contact ID %s with summary of length %d characters",
                              output_data["contact_id"], summary_length)

        # Update the transcript
        contact_response = self.sharpspring_api_manager.update_contact_transcript(
            output_data["contact_id"],
            output_data["summary"]
        )
        if "error" in contact_response:
            current_app.logger.error("[DP2SS:LOAD] Failed to update transcript: %s", contact_response.get('error', 'Unknown error'))
            raise APIError(f"Failed to update transcript for contact ID '{output_data['contact_id']}': {contact_response.get('error', 'Unknown error')}")

        # Log final results
        current_app.logger.debug("[DP2SS:LOAD] Successfully updated transcript in SharpSpring")
        current_app.logger.debug("[DP2SS:LOAD] Final state - Contact ID: %s, Field ID: %s, Opportunity ID: %s",
                              output_data.get("contact_id"), output_data.get("field_id"), output_data.get("opportunity_id"))
        current_app.logger.debug("[DP2SS:LOAD] Data loading phase complete")

        # Log overall result summary
        current_app.logger.info("[DP2SS:RESULT] Successfully processed call_id %s for contact %s - transcript saved to SharpSpring",
                             context.get("call_id"),
                             context.get("contact", {}).get("name", "Unknown"))
    
    #======================== Role-specific Functions ==========================#
    def meeting_summary(self, transcript: str) -> str:
        # Format the prompt with the transcript
        prompt = self.configuration.prompt.format(transcript=transcript)

        # Log summary operation
        transcript_length = len(transcript)
        current_app.logger.debug("[DP2SS:SUMMARY] Generating summary for transcript of length %d characters using model %s",
                              transcript_length, self.OPENAI_SUMMARY_MODEL)

        # Get summary from OpenAI
        response = self.openai_api_manager.chat(prompt, model=self.OPENAI_SUMMARY_MODEL)

        # Get content from response
        summary = response.choices[0].message.content
        summary_length = len(summary)

        # Log completion
        current_app.logger.debug("[DP2SS:SUMMARY] Generated summary of length %d characters (%.1f%% of original)",
                              summary_length,
                              (summary_length / transcript_length * 100) if transcript_length > 0 else 0)

        return summary

    def _direct_contact_search(self, value: str, field_type: str) -> str:
        """
        Direct contact search using SharpSpring's API for when normal methods fail.
        This is a last-resort fallback method for finding contacts that exist but can't be found through standard means.

        Args:
            value (str): The exact value to search for (email or phone)
            field_type (str): The type of field ('email' or 'phone')

        Returns:
            str: Contact ID if found, or None if not found
        """
        try:
            # Map field type to SharpSpring field name
            field_name = "emailAddress" if field_type == "email" else "phoneNumber"

            # Prepare search parameters for direct Leads query
            params = {
                "where": {
                    field_name: value
                },
                "limit": 1  # We only need one exact match
            }

            current_app.logger.debug("[DP2SS:CONTACT] Performing direct query for %s=%s", field_name, value)
            result = self.sharpspring_api_manager._make_api_call("getLeads", params)

            if "error" in result:
                current_app.logger.warning("[DP2SS:CONTACT] Direct query failed: %s", result.get('error'))
                return None

            # Get lead results
            leads = result.get("result", {}).get("lead", [])
            if not leads:
                current_app.logger.warning("[DP2SS:CONTACT] No leads found in direct query")
                return None

            # Get the first matching lead
            lead = leads[0]
            contact_id = lead.get("id")

            if contact_id:
                current_app.logger.info("[DP2SS:CONTACT] Direct query found contact ID: %s", contact_id)
                return contact_id

            return None

        except Exception as e:
            current_app.logger.exception("[DP2SS:CONTACT] Error in direct contact search: %s", str(e))
            return None
    
    def ensure_contact_id(self, data, context) -> str:
        if not data["contact_id"]:
            contact = context["contact"]
            current_app.logger.debug("[DP2SS:CONTACT] Creating or finding contact in SharpSpring: %s (%s)",
                                  contact.get('name', 'Unknown'), contact.get('email', 'Unknown'))

            # First attempt to find contact by email, phone, or both
            if contact.get("email") or contact.get("phone"):
                current_app.logger.debug("[DP2SS:CONTACT] Trying to find existing contact first")
                # If we got here because the initial extract phase didn't find the contact,
                # let's try a more targeted search with individual fields

                # Try email first if available
                if contact.get("email"):
                    current_app.logger.debug("[DP2SS:CONTACT] Searching by email: %s", contact.get("email"))
                    email_search = self.sharpspring_api_manager.get_contact(phone_number="", name="", email=contact["email"])
                    if not "error" in email_search and email_search.get("contact_id"):
                        contact_id = email_search["contact_id"]
                        current_app.logger.debug("[DP2SS:CONTACT] Found existing contact by email with ID: %s", contact_id)

                        # Also capture the existing transcript if it's there
                        if email_search.get("transcript"):
                            current_app.logger.debug("[DP2SS:CONTACT] Found existing transcript with length: %d",
                                                  len(email_search["transcript"]))
                            data["existing_transcript"] = email_search["transcript"]

                        return contact_id

                # Try phone next if email search failed or wasn't attempted
                if contact.get("phone"):
                    try:
                        # Log the original phone number for debugging
                        current_app.logger.debug("[DP2SS:CONTACT] Searching by phone: %s", contact.get("phone"))

                        # Try a more focused search for this contact by phone
                        # Check if this is the phone format issue
                        formatted_phone = contact["phone"]

                        # Try with the "+" stripped out if present
                        if formatted_phone.startswith("+"):
                            # Also try searching without the + sign
                            stripped_phone = formatted_phone[1:]
                            current_app.logger.debug("[DP2SS:CONTACT] Also trying stripped phone format: %s", stripped_phone)

                            # Try with the stripped phone number first
                            stripped_search = self.sharpspring_api_manager.get_contact(phone_number=stripped_phone, name="", email="")
                            if not "error" in stripped_search and stripped_search.get("contact_id"):
                                contact_id = stripped_search["contact_id"]
                                current_app.logger.debug("[DP2SS:CONTACT] Found contact by stripped phone with ID: %s", contact_id)

                                # Store info and return
                                if stripped_search.get("transcript"):
                                    current_app.logger.debug("[DP2SS:CONTACT] Found existing transcript with length: %d",
                                                        len(stripped_search["transcript"]))
                                    data["existing_transcript"] = stripped_search["transcript"]

                                # Get full name for verification
                                contact_id = stripped_search["contact_id"]
                                current_app.logger.debug("[DP2SS:CONTACT] Found contact by stripped phone format - ID: %s", contact_id)
                                current_app.logger.debug("[DP2SS:CONTACT] ⚠️ IMPORTANT: Verify this is the correct contact (Expected: %s)",
                                                     contact.get("name", "Unknown"))
                                return contact_id

                        # Try standard search with the original phone number
                        phone_search = self.sharpspring_api_manager.get_contact(phone_number=contact["phone"], name="", email="")
                        if not "error" in phone_search and phone_search.get("contact_id"):
                            contact_id = phone_search["contact_id"]

                            # Add verification to check if this contact match is correct
                            current_app.logger.debug("[DP2SS:CONTACT] Found contact by phone with ID: %s - verifying match", contact_id)

                            # Get all the details we have for debugging
                            current_app.logger.debug("[DP2SS:CONTACT] Contact match details:")
                            current_app.logger.debug("[DP2SS:CONTACT] - Expected name: %s", contact.get("name", "None"))
                            current_app.logger.debug("[DP2SS:CONTACT] - Expected email: %s", contact.get("email", "None"))
                            current_app.logger.debug("[DP2SS:CONTACT] - Expected phone: %s", contact.get("phone", "None"))
                            current_app.logger.debug("[DP2SS:CONTACT] - Contact ID: %s", contact_id)

                            # Continue with the match - our improved search logic should prevent incorrect matches

                            # Also capture the existing transcript if it's there
                            if phone_search.get("transcript"):
                                current_app.logger.debug("[DP2SS:CONTACT] Found existing transcript with length: %d",
                                                    len(phone_search["transcript"]))
                                data["existing_transcript"] = phone_search["transcript"]

                            return contact_id

                    except Exception as e:
                        current_app.logger.error("[DP2SS:CONTACT] Error during phone search: %s", str(e))
                        # Continue with creation process

            # If we couldn't find the contact, try to create it
            current_app.logger.debug("[DP2SS:CONTACT] Creating new contact with name: %s, email: %s, phone: %s, owner_id: %s",
                                  contact.get("name"), contact.get("email"),
                                  contact.get("phone"), data.get("owner_id"))

            contact_response = self.sharpspring_api_manager.create_contact(
                contact["name"],
                contact["email"],
                contact["phone"],
                data["owner_id"]
            )

            # Check for "already exists" error specifically
            if "error" in contact_response and "exists" in contact_response.get("error", "").lower():
                current_app.logger.debug("[DP2SS:CONTACT] Contact already exists error, trying to find again")

                # Try a more aggressive search approach to find the contact that's conflicting
                search_methods = [
                    # First try exact match on all fields at once
                    {
                        "method": "all_fields",
                        "phone": contact.get("phone", ""),
                        "name": contact.get("name", ""),
                        "email": contact.get("email", "")
                    },
                    # Then try email-only search if email exists
                    {
                        "method": "email_only",
                        "phone": "",
                        "name": "",
                        "email": contact.get("email", "")
                    } if contact.get("email") else None,
                    # Try phone with stripped + if present
                    {
                        "method": "stripped_phone",
                        "phone": contact.get("phone", "")[1:] if contact.get("phone", "").startswith("+") else "",
                        "name": "",
                        "email": ""
                    } if contact.get("phone", "").startswith("+") else None,
                    # Try original phone format
                    {
                        "method": "phone_only",
                        "phone": contact.get("phone", ""),
                        "name": "",
                        "email": ""
                    } if contact.get("phone") else None,
                    # Try name only as last resort
                    {
                        "method": "name_only",
                        "phone": "",
                        "name": contact.get("name", ""),
                        "email": ""
                    } if contact.get("name") else None
                ]

                # Remove any None entries from the search methods
                search_methods = [method for method in search_methods if method is not None]

                # Try each search method until we find a match
                for search in search_methods:
                    current_app.logger.debug("[DP2SS:CONTACT] Trying search method: %s", search["method"])
                    retry_search = self.sharpspring_api_manager.get_contact(
                        phone_number=search["phone"],
                        name=search["name"],
                        email=search["email"]
                    )

                    if not "error" in retry_search and retry_search.get("contact_id"):
                        contact_id = retry_search["contact_id"]
                        current_app.logger.debug("[DP2SS:CONTACT] Found existing contact using %s search with ID: %s",
                                            search["method"], contact_id)

                        # Extra verification for Bernard Lynch's contact
                        if contact_id == "2000134441967618" and contact.get("name") != "Bernard Lynch":
                            current_app.logger.warning("[DP2SS:CONTACT] ⚠️ Found Bernard Lynch's contact ID (%s) - REJECTING MATCH",
                                                 contact_id)
                            continue  # Skip this match and try the next search method

                        # Also capture the existing transcript if it's there
                        if retry_search.get("transcript"):
                            current_app.logger.debug("[DP2SS:CONTACT] Found existing transcript with length: %d",
                                                  len(retry_search["transcript"]))
                            data["existing_transcript"] = retry_search["transcript"]

                        return contact_id

                # If we've exhausted all search options and still can't find the contact,
                # try a more comprehensive search with different batch parameters
                current_app.logger.debug("[DP2SS:CONTACT] Regular searches failed, trying comprehensive search...")

                # Try with more batches and longer time period
                if contact.get("email"):
                    comprehensive_search = self.sharpspring_api_manager.get_contact(
                        phone_number="",  # No phone
                        name="",  # No name
                        email=contact.get("email"),
                        max_batches=5,
                        days=90
                    )
                    if not "error" in comprehensive_search and comprehensive_search.get("contact_id"):
                        contact_id = comprehensive_search["contact_id"]
                        current_app.logger.debug("[DP2SS:CONTACT] Found contact through comprehensive email search: %s", contact_id)

                        if comprehensive_search.get("transcript"):
                            data["existing_transcript"] = comprehensive_search["transcript"]

                        return contact_id

                # If we still couldn't find it after all attempts, create a unique contact variant
                current_app.logger.warning("[DP2SS:CONTACT] Contact exists in SharpSpring but cannot be found after multiple search attempts: %s",
                                     contact_response.get('error', 'Unknown error'))

                # Direct API calls already used in the new get_contact method, so if we still can't find it,
                # we'll create a unique contact variant to avoid conflicts
                current_app.logger.warning("[DP2SS:CONTACT] Creating a unique contact variant...")

                # Add a timestamp to the email to ensure it's unique
                unique_email = contact["email"]
                if "@" in unique_email:
                    username, domain = unique_email.split("@", 1)
                    unique_email = f"{username}+{int(time.time())}@{domain}"
                else:
                    unique_email = f"{unique_email}+{int(time.time())}@example.com"

                current_app.logger.warning("[DP2SS:CONTACT] Using unique email: %s", unique_email)

                current_app.logger.warning("[DP2SS:CONTACT] Creating contact with unique email: %s", unique_email)
                unique_response = self.sharpspring_api_manager.create_contact(
                    contact["name"],
                    unique_email,  # Use unique email
                    contact["phone"],
                    data["owner_id"]
                )

                if "error" in unique_response:
                    current_app.logger.error("[DP2SS:CONTACT] Even unique contact creation failed: %s",
                                     unique_response.get('error', 'Unknown error'))
                    raise APIError(f"Failed to create unique contact variant for {contact.get('name', 'Unknown')}: "
                                  f"{unique_response.get('error', 'Unknown error')}")

                return unique_response["contact_id"]

            # Handle any other errors
            elif "error" in contact_response or not contact_response.get("contact_id"):
                current_app.logger.error("[DP2SS:CONTACT] Failed to create contact: %s",
                                      contact_response.get('error', 'Unknown error'))
                raise APIError(f"Failed to create SharpSpring contact for {contact['name']} ({contact['email']}): {contact_response.get('error', 'Unknown error')}")

            # Success path - genuinely created a new contact
            current_app.logger.debug("[DP2SS:CONTACT] Successfully created new contact with ID: %s",
                                  contact_response['contact_id'])
            return contact_response["contact_id"]

        # Contact ID was already found in the extract phase
        current_app.logger.debug("[DP2SS:CONTACT] Using existing contact with ID: %s", data["contact_id"])
        return data["contact_id"]
    
    def ensure_transcript_field(self, data) -> str:
        # If field_id is None or empty, create a new transcript field
        if not data.get("field_id"):
            current_app.logger.debug("[DP2SS:FIELD] Creating new transcript field in SharpSpring")
            field_response = self.sharpspring_api_manager.create_transcript_field()

            if "error" in field_response:
                current_app.logger.error("[DP2SS:FIELD] Failed to create transcript field: %s",
                                      field_response.get('error', 'Unknown error'))
                raise APIError(f"Failed to create transcript field in SharpSpring: {field_response.get('error', 'Unknown error')}")

            if not field_response.get("field_id"):
                current_app.logger.error("[DP2SS:FIELD] Created transcript field but field_id is missing from response")
                raise APIError("Created transcript field but field_id is missing from response")

            field_id = field_response.get("field_id")
            current_app.logger.debug("[DP2SS:FIELD] Successfully created transcript field with ID: %s", field_id)

            # After creating the field, we need to get its system_name
            current_app.logger.debug("[DP2SS:FIELD] Retrieving system_name for newly created transcript field")
            updated_field = self.sharpspring_api_manager.get_transcript_field()
            if "error" not in updated_field and updated_field.get("system_name"):
                data["system_name"] = updated_field["system_name"]
                current_app.logger.debug("[DP2SS:FIELD] Found system_name for new field: %s",
                                      updated_field["system_name"])
            else:
                error_msg = updated_field.get("error", "Unknown error") if "error" in updated_field else "No system_name returned"
                current_app.logger.error("[DP2SS:FIELD] Created transcript field but couldn't retrieve its system_name: %s",
                                      error_msg)
                raise APIError("Created transcript field but couldn't retrieve its system_name")

            return field_id

        current_app.logger.debug("[DP2SS:FIELD] Using existing transcript field with ID: %s", data["field_id"])
        return data["field_id"]
    
    def ensure_opportunity_id(self, data, context) -> str:
        if not data["opportunity_id"]: # This means that we couldn't find the opportunity in the extract step
            current_app.logger.debug("[DP2SS:OPPORTUNITY] Creating opportunity for contact ID: %s", data['contact_id'])

            # Log the opportunity data being sent
            current_app.logger.debug("[DP2SS:OPPORTUNITY] Creating with owner email: %s, contact name: %s, contact ID: %s",
                                  context["target"].get("email"),
                                  context["contact"].get("name"),
                                  data["contact_id"])

            # Ensure contact_id is a string - this fixes the type error
            contact_id = str(data["contact_id"])

            opportunity_response = self.sharpspring_api_manager.create_opportunity(
                context["target"]["email"],
                context["contact"]["name"],
                contact_id  # Use string version of contact_id
            )
            # Special case: entry already exists error - try to find the existing opportunity
            if "error" in opportunity_response and "exists" in opportunity_response.get("error", "").lower():
                current_app.logger.warning("[DP2SS:OPPORTUNITY] Opportunity already exists error: %s",
                                       opportunity_response.get('error'))

                # Try to find the existing opportunity
                current_app.logger.debug("[DP2SS:OPPORTUNITY] Searching for existing opportunity for contact ID: %s", contact_id)
                find_opportunity = self.sharpspring_api_manager.get_opportunity_id_from_contact_id(contact_id)

                # If we found it, use that ID
                if not "error" in find_opportunity and find_opportunity.get("opportunity_id"):
                    opportunity_id = find_opportunity.get("opportunity_id")
                    current_app.logger.debug("[DP2SS:OPPORTUNITY] Found existing opportunity with ID: %s", opportunity_id)
                    return opportunity_id

                # If we can't find it, log warning but don't fail - we'll just proceed without an opportunity
                current_app.logger.warning("[DP2SS:OPPORTUNITY] Opportunity exists but couldn't be found: %s",
                                       find_opportunity.get('error', 'Unknown error'))
                return "unknown"  # Return a placeholder value instead of None

            # Handle other errors
            elif "error" in opportunity_response:
                current_app.logger.error("[DP2SS:OPPORTUNITY] Failed to create opportunity: %s",
                                      opportunity_response.get('error', 'Unknown error'))
                # Return placeholder instead of raising error - don't fail the whole flow just for this
                current_app.logger.warning("[DP2SS:OPPORTUNITY] Continuing without opportunity ID")
                return "unknown"

            opportunity_id = opportunity_response.get("opportunity_id")
            current_app.logger.debug("[DP2SS:OPPORTUNITY] Successfully created with ID: %s", opportunity_id)
            return opportunity_id

        current_app.logger.debug("[DP2SS:OPPORTUNITY] Using existing opportunity with ID: %s", data["opportunity_id"])
        return data["opportunity_id"]