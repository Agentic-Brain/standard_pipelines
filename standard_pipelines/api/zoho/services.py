from __future__ import annotations

from flask import current_app
from standard_pipelines.api.services import BaseAPIManager
from standard_pipelines.data_flow.exceptions import APIError

# from zoho import Zoho
# from zoho.crm.associations import BatchInputPublicObjectId
# from zoho.crm.contacts import SimplePublicObject as ContactObject, SimplePublicObjectWithAssociations as ContactObjectWithAssociations
# from zoho.crm.deals import SimplePublicObject as DealObject, SimplePublicObjectWithAssociations as DealObjectWithAssociations
# from zoho.crm.objects.meetings import SimplePublicObject as MeetingObject
# from zoho.crm.objects.notes import SimplePublicObject as NoteObject
# from zoho.crm.associations.v4 import AssociationSpec
# from zoho.files import ApiException

import typing as t
from types import MappingProxyType


from abc import ABCMeta, abstractmethod


class ZohoAPIManager(BaseAPIManager, metaclass=ABCMeta):

    def __init__(self, api_config: dict) -> None:
        super().__init__(api_config)
        self._api_client = ZCRMRestClient()
        self._api_client.access_token = self.access_token

    @property
    def required_config(self) -> list[str]:
        return ["client_id", "client_secret", "refresh_token"]

    @property
    def access_token(self) -> str:
        return self._api_client.oauth.tokens_api.create(
            grant_type="refresh_token",
            client_id=self.api_config["client_id"],
            client_secret=self.api_config["client_secret"],
            refresh_token=self.api_config["refresh_token"],
        ).access_token #type: ignore

    def all_contacts(self) -> list[dict]:
        return [contact.to_dict() for contact in self._api_client.crm.contacts.get_all()]
    
    def all_owners(self) -> list[dict]:
        return self._api_client.settings.users.users_api.get_page(limit=100).to_dict()["results"] #type: ignore
    
    def all_users(self) -> list[dict]:
        return [user.to_dict() for user in self._api_client.crm.objects.get_all(object_type="user")]

    def contact_by_contact_id(self, contact_id: str, properties: list[str] = []) -> dict:
        contact: ContactObjectWithAssociations = self._api_client.crm.contacts.basic_api.get_by_id(contact_id, properties=properties) #type: ignore
        return contact.to_dict()

    def deal_by_deal_id(self, deal_id: str, properties: list[str] = []) -> dict:
        deal: DealObjectWithAssociations = self._api_client.crm.deals.basic_api.get_by_id(deal_id, properties=properties) #type: ignore
        return deal.to_dict()

    def user_by_email(self, email: str) -> dict:
        all_users = self.all_owners()
        matching_users = []
        for user in all_users:
            if user.get("email") == None:
                current_app.logger.warning(f"Hubspot user {user['properties']['hs_object_id']} has no email.")
            elif user["email"] == email:
                matching_users.append(user)
        if len(matching_users) > 1:
            error_msg = f"Multiple users found for email {email}."
            raise APIError(error_msg)
        if len(matching_users) == 0:
            error_msg = f"No user found for email {email}."
            raise APIError(error_msg)
        return matching_users[0]

    def contact_by_name_or_email(self, name: t.Optional[str] = None, email: t.Optional[str] = None) -> dict:
        all_contacts = self.all_contacts()
        matching_contacts = []
        for contact in all_contacts:
            contact_first_name = contact.get("properties", {}).get("firstname", "")
            contact_last_name = contact.get("properties", {}).get("lastname", "")
            contact_full_name = f"{contact_first_name} {contact_last_name}".strip()
            contact_email = contact.get("properties", {}).get("email", "")
            if (
                name is not None and contact_full_name == name
                or email is not None and contact_email == email
            ):
                matching_contacts.append(contact)
        if len(matching_contacts) > 1: # TODO: better error handling
            error_msg = f"Multiple contacts found for {email} or {name}."
            raise APIError(error_msg)
        if len(matching_contacts) == 0:
            error_msg = f"No contact found for {email} or {name}."
            raise APIError(error_msg)
        return matching_contacts[0]

    def deal_by_contact_id(self, contact_id: str) -> dict:
        batch_ids = BatchInputPublicObjectId([{"id": contact_id}])
        deal_associations = self._api_client.crm.associations.batch_api.read(
            from_object_type="contacts",
            to_object_type="deals",
            batch_input_public_object_id=batch_ids,
        ).to_dict()["results"] #type: ignore
        if len(deal_associations) > 1:
            error_msg = f"Multiple deals found for contact {contact_id}."
            raise APIError(error_msg)
        if len(deal_associations) == 0:
            error_msg = f"No deal found for contact {contact_id}."
            raise APIError(error_msg)
        deal_association_to = deal_associations[0]["to"]
        contact_to_deal_associations = []
        for deal_association in deal_association_to:
            if deal_association["type"] == "contact_to_deal":
                contact_to_deal_associations.append(deal_association)
        if len(contact_to_deal_associations) > 1:
            error_msg = f"Multiple deals found for contact {contact_id}."
            raise APIError(error_msg)
        if len(contact_to_deal_associations) == 0:
            error_msg = f"No deal found for contact {contact_id}."
            raise APIError(error_msg)
        deal_id = contact_to_deal_associations[0]["id"]
        return self.deal_by_deal_id(deal_id)

    def zoho_association_object(self, to_id: str, association_id: str, association_category: str = "ZOHO_DEFINED") -> dict:
        return {
            "to": {
                "id": to_id
            },
            "types": [
                {
                    "associationCategory": association_category,
                    "associationTypeId": association_id
                }
            ]
        }

    def create_contact(self, contact_object: CreatableContactZohoObject) -> ExtantContactZohoObject:
        contact: ContactObject = self._api_client.crm.contacts.basic_api.create(contact_object.zoho_object_dict)
        return ExtantContactZohoObject(contact.to_dict(), self)

    def create_deal(self, deal_object: CreatableDealZohoObject) -> ExtantDealZohoObject:
        deal: DealObject = self._api_client.crm.deals.basic_api.create(deal_object.zoho_object_dict)
        return ExtantDealZohoObject(deal.to_dict(), self)

    def create_meeting(self, meeting_object: CreatableMeetingZohoObject) -> ExtantMeetingZohoObject:
        meeting: MeetingObject = self._api_client.crm.objects.meetings.basic_api.create(meeting_object.zoho_object_dict)
        return ExtantMeetingZohoObject(meeting.to_dict(), self)

    def create_note(self, note_object: CreatableNoteZohoObject) -> ExtantNoteZohoObject:
        note: NoteObject = self._api_client.crm.objects.notes.basic_api.create(note_object.zoho_object_dict)
        return ExtantNoteZohoObject(note.to_dict(), self)

class ZohoObject(metaclass=ABCMeta):

    # Magic numbers to associate various types of HubSpot objects
    # Docs: https://developers.hubspot.com/docs/guides/api/crm/associations/associations-v4#association-type-id-values
    ASSOCIATION_TYPES = MappingProxyType({
        ("deal", "contact"): 3,
        ("meeting", "contact"): 200,
        ("meeting", "deal"): 212,
        ("note", "deal"): 214,
    })

    def __init__(self, zoho_object_dict: dict, api_manager: ZohoAPIManager):
        self.zoho_object_dict = zoho_object_dict
        self.api_manager = api_manager

    def association_type_id(self, from_type: str, to_type: str) -> int:
        association_type_id = self.ASSOCIATION_TYPES.get((from_type, to_type))
        if association_type_id is None:
            raise ValueError(
                f"No association type ID found from {from_type} to {to_type}."
            )
        return association_type_id

    @abstractmethod
    def add_association(self, to_object: ExtantZohoObject) -> None:
        pass

    @abstractmethod
    def evaluate(self) -> ExtantZohoObject:
        pass

    @property
    @abstractmethod
    def zoho_type(self) -> str:
        pass

class ExtantZohoObject(ZohoObject, metaclass=ABCMeta):

    def add_association(self, to_object: ExtantZohoObject) -> None:
        association_id = self.association_type_id(self.zoho_type, to_object.zoho_type)
        self.api_manager._api_client.crm.associations.v4.basic_api.create(
            object_type=self.zoho_type,
            object_id=self.zoho_object_dict["id"],
            to_object_type=to_object.zoho_type,
            to_object_id=to_object.zoho_object_dict["id"],
            association_spec=[AssociationSpec(association_category="ZOHO_DEFINED", association_type_id=association_id)],
        )

    def evaluate(self) -> t.Self:
        return self

ExtantZohoObjectType = t.TypeVar("ExtantZohoObjectType", bound=ExtantZohoObject)

class CreatableZohoObject(t.Generic[ExtantZohoObjectType], ZohoObject, metaclass=ABCMeta):

    @property
    @abstractmethod
    def creation_function(self) -> t.Callable[[CreatableZohoObject], ExtantZohoObjectType]:
        pass

    def add_association(self, to_object: ExtantZohoObject) -> None:
        association_id = self.association_type_id(self.zoho_type, to_object.zoho_type)
        association_object = self.api_manager.zoho_association_object(to_object.zoho_object_dict["id"], association_id)
        if "associations" not in self.zoho_object_dict:
            self.zoho_object_dict["associations"] = []
        self.zoho_object_dict["associations"].append(association_object)

    def evaluate(self) -> ExtantZohoObjectType:
        return self.creation_function(self)

class ExtantContactZohoObject(ExtantZohoObject):

    zoho_type: str = "contact"

class ExtantDealZohoObject(ExtantZohoObject):

    zoho_type: str = "deal"

class ExtantMeetingZohoObject(ExtantZohoObject):

    zoho_type: str = "meeting"

class ExtantNoteZohoObject(ExtantZohoObject):

    zoho_type: str = "note"

class ExtantUserZohoObject(ExtantZohoObject):

    zoho_type: str = "user"

class CreatableContactZohoObject(CreatableZohoObject[ExtantContactZohoObject]):

    zoho_type: str = "contact"

    @property
    def creation_function(self) -> t.Callable[[CreatableContactZohoObject], ExtantContactZohoObject]:
        return self.api_manager.create_contact

class CreatableDealZohoObject(CreatableZohoObject[ExtantDealZohoObject]):

    zoho_type: str = "deal"

    def add_owner_from_user(self, user: ExtantUserZohoObject) -> None:
        self.zoho_object_dict["properties"]["zoho_owner_id"] = user.zoho_object_dict["id"]

    @property
    def creation_function(self) -> t.Callable[[CreatableDealZohoObject], ExtantDealZohoObject]:
        return self.api_manager.create_deal

class CreatableMeetingZohoObject(CreatableZohoObject[ExtantMeetingZohoObject]):

    zoho_type: str = "meeting"

    def add_owner_from_deal(self, deal: ExtantDealZohoObject) -> None:
        self.zoho_object_dict["properties"]["zoho_owner_id"] = deal.zoho_object_dict["properties"]["zoho_owner_id"]

    @property
    def creation_function(self) -> t.Callable[[CreatableMeetingZohoObject], ExtantMeetingZohoObject]:
        return self.api_manager.create_meeting

class CreatableNoteZohoObject(CreatableZohoObject[ExtantNoteZohoObject]):

    zoho_type: str = "note"

    def add_owner_from_deal(self, deal: ExtantDealZohoObject) -> None:
        self.zoho_object_dict["properties"]["zoho_owner_id"] = deal.zoho_object_dict["properties"]["zoho_owner_id"]

    @property
    def creation_function(self) -> t.Callable[[CreatableNoteZohoObject], ExtantNoteZohoObject]:
        return self.api_manager.create_note

