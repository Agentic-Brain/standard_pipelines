from __future__ import annotations
import json
import time
import typing as t

from flask import current_app
from standard_pipelines.api.services import BaseAPIManager
from standard_pipelines.data_flow.exceptions import APIError

from zohocrmsdk.src.com.zoho.crm.api import Initializer, ParameterMap, HeaderMap
from zohocrmsdk.src.com.zoho.crm.api.dc import USDataCenter
from zohocrmsdk.src.com.zoho.api.authenticator import OAuthToken
from zohocrmsdk.src.com.zoho.crm.api.util import APIResponse, Choice
from zohocrmsdk.src.com.zoho.crm.api.record.api_exception import APIException

# Zoho Record API imports
from zohocrmsdk.src.com.zoho.crm.api.record import (
    RecordOperations,
    BodyWrapper,
    Record as ZCRMRecord,
    GetRecordsParam,
    SearchRecordsParam,
    Field
)
from zohocrmsdk.src.com.zoho.crm.api.record.action_wrapper import ActionWrapper

from zohocrmsdk.src.com.zoho.crm.api.users import UsersOperations

from abc import ABCMeta, abstractmethod
from types import MappingProxyType

from .models import ZohoCredentials

class ZohoAPIManager(BaseAPIManager, metaclass=ABCMeta):

    def __init__(self, creds: ZohoCredentials) -> None:
        super().__init__(creds)
        environment = USDataCenter.PRODUCTION()
        self.token: OAuthToken = OAuthToken(
            client_id=creds.oauth_client_id,
            client_secret=creds.oauth_client_secret,
            refresh_token=creds.oauth_refresh_token,
            access_token=creds.oauth_access_token
        )
        # there's an error in zoho, expires_in is actually expires_at
        # self.token.set_expires_in(str(creds.oauth_expires_at))

        # initialize the Zoho CRM SDK (this sets a thread-local client)
        try:
            Initializer.initialize(environment=environment, token=self.token)
        except Exception as e:
            current_app.logger.exception(f"Error initializing Zoho CRM SDK: {e}")
    @property
    def required_config(self) -> list[str]:
        return ["client_id", "oauth_client_id", "oauth_client_secret"]

    @property
    def access_token(self) -> str:
        # Refresh token if expired.
        expires_at: int = int(self.token.get_expires_in())
        cur_time_ms: int = int(time.time() * 1000)
        if cur_time_ms >= expires_at:
            self.token.refresh_access_token()
        return self.token.get_access_token()

    def get_all_contacts(self) -> list[dict]:
        record_ops = RecordOperations("Contacts")
        params = GetRecordsParam()
        params.set_page(1)
        params.set_per_page(200)
        response = record_ops.get_records("Contacts", params)
        records = []
        if response.get_object():
            data = response.get_object().get_data()
            for record in data:
                records.append(record.to_dict())
        return records

    def get_all_owners(self) -> list[dict]:
        users_ops = UsersOperations()
        response = users_ops.get_users()
        owners = []
        if response.get_object():
            data = response.get_object().get_users()
            for user in data:
                owners.append(user.to_dict())
        return owners

    def get_all_users(self) -> list[dict]:
        # In Zoho, owners and users are essentially the same.
        return self.get_all_owners()

    def get_contact_by_contact_id(self, contact_id: str, properties: list[str] = []) -> dict:
        record_ops = RecordOperations()
        response = record_ops.get_record(int(contact_id), "Contacts")
        if response.get_object() and response.get_object().get_data():
            return response.get_object().get_data()[0].to_dict()
        else:
            raise APIError(f"Contact with id {contact_id} not found.")

    def get_deal_by_deal_id(self, deal_id: str, properties: list[str] = []) -> dict:
        record_ops = RecordOperations()
        response = record_ops.get_record(int(deal_id), "Deals")
        if response.get_object() and response.get_object().get_data():
            return response.get_object().get_data()[0].to_dict()
        else:
            raise APIError(f"Deal with id {deal_id} not found.")

    def get_user_by_email(self, email: str) -> dict:
        users = self.get_all_owners()
        matching_users = []
        for user in users:
            user_email = user.get("email")
            if not user_email:
                current_app.logger.warning(f"Zoho user {user.get('id')} has no email.")
            elif user_email.lower() == email.lower():
                matching_users.append(user)
        if len(matching_users) > 1:
            raise APIError(f"Multiple users found for email {email}.")
        if not matching_users:
            raise APIError(f"No user found for email {email}.")
        return matching_users[0]

    def get_contact_by_name_or_email(self, name: t.Optional[str] = None, email: t.Optional[str] = None) -> dict:
        contacts = self.get_all_contacts()
        matching_contacts = []
        for contact in contacts:
            first_name = contact.get("First_Name", "")
            last_name = contact.get("Last_Name", "")
            full_name = f"{first_name} {last_name}".strip()
            contact_email = contact.get("Email", "")
            if (name and full_name.lower() == name.lower()) or (email and contact_email.lower() == email.lower()):
                matching_contacts.append(contact)
        if len(matching_contacts) > 1:
            raise APIError(f"Multiple contacts found for {email or name}.")
        if not matching_contacts:
            raise APIError(f"No contact found for {email or name}.")
        return matching_contacts[0]
    
    def get_contact_by_email(self, email: t.Optional[str] = None) -> dict:
        record_ops = RecordOperations("Contacts")
        params = ParameterMap()
        params.add(SearchRecordsParam.email, email)
        response : APIResponse = record_ops.search_records(params)

        current_app.logger.debug(f"get_contact_by_email: {response.get_status_code(), response.get_object()}")

        if response.get_status_code() == 204:
            return None
        
        
        return response.get_object()
    
    def get_deal_by_contact_id(self, contact_id: str) -> dict:
        # In Zoho, assume the deal has a lookup field "Contact_Name" linking to a contact.
        record_ops = RecordOperations()
        params = SearchRecordsParam()
        # Use criteria to search for deals where the "Contact_Name" field equals the given contact_id.
        params.set_criteria(f"(Contact_Name:equals:{contact_id})")
        response = record_ops.search_records("Deals", params)
        if response.get_object() and response.get_object().get_data():
            deals = response.get_object().get_data()
            if len(deals) > 1:
                raise APIError(f"Multiple deals found for contact {contact_id}.")
            return deals[0].to_dict()
        else:
            raise APIError(f"No deal found for contact {contact_id}.")

    def zoho_association_object(self, to_id: str, association_id: str, association_category: str = "ZOHO_DEFINED") -> dict:
        # This method is retained for compatibility, but note that in Zoho associations
        # are typically handled via lookup fields rather than a separate API call.
        return {
            "to": {"id": to_id},
            "types": [{
                "associationCategory": association_category,
                "associationTypeId": association_id,
            }]
        }

    def create_contact(self,  contact : dict):
        record_ops = RecordOperations("Contacts")
        request = BodyWrapper()

        record = ZCRMRecord()
        record.add_field_value(Field.Contacts.email(), contact['email'])
        # record.add_field_value(Field.Contacts.first_name, contact['first_name'])
        # record.add_field_value(Field.Contacts.last_name, contact['last_name'])

        request.set_data([record])

        response : APIResponse = record_ops.create_records(request)

        current_app.logger.debug(f"create_contact: {response.get_status_code(), response.get_object()}")

        if response.get_status_code() == 400:
            payload : ActionWrapper = response.get_object()
            data : list[APIException] = payload.get_data()
            for exception in data:
                current_app.logger.exception(f"Error creating contact: {exception.get_code()} {exception.get_details()}")

        return response.get_object()

        # Map the provided dictionary to a Zoho record.
        for key, value in contact_object.items():
            record.add_key_value(key, value)
        
        request.set_data([record])
        record_ops = RecordOperations()
        response = record_ops.create_records("Contacts", request)
        if response.get_object() and response.get_object().get_data():
            created_record = response.get_object().get_data()[0]
            return created_record
        else:
            raise APIError("Failed to create contact.")

    def create_deal(self, deal_object):
        record = ZCRMRecord()
        for key, value in deal_object.zoho_object_dict.items():
            record.add_key_value(key, value)
        request = BodyWrapper()
        request.set_data([record])
        record_ops = RecordOperations()
        response = record_ops.create_records("Deals", request)
        if response.get_object() and response.get_object().get_data():
            created_record = response.get_object().get_data()[0]
            return created_record
        else:
            raise APIError("Failed to create deal.")

    def create_meeting(self, meeting_object):
        record = ZCRMRecord()
        for key, value in meeting_object.zoho_object_dict.items():
            record.add_key_value(key, value)
        request = BodyWrapper()
        request.set_data([record])
        record_ops = RecordOperations()
        response = record_ops.create_records("Meetings", request)
        if response.get_object() and response.get_object().get_data():
            created_record = response.get_object().get_data()[0]
            return created_record.to_dict()
        else:
            raise APIError("Failed to create meeting.")

    def create_note(self, note_object):
        record = ZCRMRecord()
        for key, value in note_object.zoho_object_dict.items():
            record.add_key_value(key, value)
        request = BodyWrapper()
        request.set_data([record])
        record_ops = RecordOperations()
        response = record_ops.create_records("Notes", request)
        if response.get_object() and response.get_object().get_data():
            created_record = response.get_object().get_data()[0]
            return created_record.to_dict()
        else:
            raise APIError("Failed to create note.")
