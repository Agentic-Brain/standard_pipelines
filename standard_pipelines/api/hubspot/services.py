from ..services import BaseAPIManager
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectWithAssociations
from hubspot.crm.associations import BatchInputPublicObjectId
from hubspot.crm.contacts import SimplePublicObjectInput as ContactInput
from hubspot.crm.deals import SimplePublicObjectInput as DealInput
from hubspot.files import ApiException
from standard_pipelines.data_flow.exceptions import APIError
from abc import ABCMeta
import typing as t

class HubSpotAPIManager(BaseAPIManager, metaclass=ABCMeta):
    def __init__(self, api_config: dict) -> None:
        super().__init__(api_config)
        self.api_client = HubSpot()
        self.api_client.access_token = self.access_token
    
    @property
    def required_config(self) -> list[str]:
        return ["client_id", "client_secret", "refresh_token"]

    @property
    def access_token(self) -> str:
        return self.api_client.oauth.tokens_api.create(
            grant_type="refresh_token",
            client_id=self.api_config["client_id"],
            client_secret=self.api_config["client_secret"],
            refresh_token=self.api_config["refresh_token"],
        ).access_token

    def all_contacts(self) -> list[dict]:
        return [contact.to_dict() for contact in self.api_client.crm.contacts.get_all()]

    def contact_by_contact_id(self, contact_id: str, properties: list[str] = []) -> dict:
        contact: SimplePublicObjectWithAssociations = self.api_client.crm.contacts.basic_api.get_by_id(contact_id, properties=properties)
        return contact.to_dict()
    
    def deal_by_deal_id(self, deal_id: str, properties: list[str] = []) -> dict:
        deal: SimplePublicObjectWithAssociations = self.api_client.crm.deals.basic_api.get_by_id(deal_id, properties=properties)
        return deal.to_dict()
    
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
        if len(matching_contacts) > 1:
            error_msg = f"Multiple contacts found for {email} or {name}."
            raise APIError(error_msg)
        if len(matching_contacts) == 0:
            error_msg = f"No contact found for {email} or {name}."
            raise APIError(error_msg)
        return matching_contacts[0]

    def deal_by_contact_id(self, contact_id: str) -> dict:
        batch_ids = BatchInputPublicObjectId([{"id": contact_id}])
        deal_associations = self.api_client.crm.associations.batch_api.read(
            from_object_type="contacts",
            to_object_type="deals",
            batch_input_public_object_id=batch_ids,
        ).to_dict()["results"]
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

    def create_contact(self, email: str | None = None, first_name: str | None = None, last_name: str | None = None) -> dict:
        props = {}
        if email:
            props["email"] = email
        if first_name:
            props["firstname"] = first_name
        if last_name:
            props["lastname"] = last_name

        contact_input = ContactInput(properties=props)

        try:
            new_contact = self.api_client.crm.contacts.basic_api.create(contact_input)
        except ApiException as e:
            raise APIError(f"Error creating contact: {e}")

        return new_contact.to_dict()

    def create_deal(self, deal_name: str, stage_id: str, contact_id: t.Optional[str] = None) -> dict:
        deal_input = DealInput(
            properties={
                "dealname": deal_name,
                "pipeline": "default",
                "dealstage": stage_id
            }
        )

        try:
            new_deal = self.api_client.crm.deals.basic_api.create(deal_input)
            deal_dict = new_deal.to_dict()
            deal_id = deal_dict.get("id")

            if not deal_id:
                raise APIError("Failed to retrieve 'id' from newly created deal.")

            if contact_id:
                batch_input = BatchInputPublicObjectId(
                    inputs=[
                        {
                            "from": {"id": contact_id},
                            "to": {"id": deal_id},
                            "type": "contact_to_deal"
                        }
                    ]
                )

                self.api_client.crm.associations.batch_api.create(
                    "contacts",
                    "deals",
                    batch_input
                )

            return deal_dict

        except ApiException as e:
            raise APIError(f"Error creating or associating deal: {e}")

    def create_meeting(self, meeting_object: dict) -> None:
        self.api_client.crm.objects.meetings.basic_api.create(meeting_object)
    
    def create_note(self, note_object: dict) -> None:
        self.api_client.crm.objects.notes.basic_api.create(note_object)
