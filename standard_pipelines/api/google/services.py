from standard_pipelines.api.google.models import GoogleCredentials
from standard_pipelines.extensions import db
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
from uuid import UUID

class GoogleCredentialsService:
    @staticmethod
    def set_default_credentials(client_id: UUID, credential_id: UUID) -> bool:
        """
        Sets a specific Google credential as the default for a client.
        Unsets any previous default credentials for the client.
        
        Args:
            client_id: The UUID of the client
            credential_id: The UUID of the credential to set as default
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the credential to set as default
            credential = GoogleCredentials.query.filter_by(
                id=credential_id,
                client_id=client_id
            ).first()
            
            if credential is None:
                return False
                
            # Set this credential as default
            credential.is_default = True
            credential.save()
            return True
            
        except SQLAlchemyError:
            db.session.rollback()
            return False
            
    @staticmethod
    def get_default_credentials(client_id: UUID) -> Optional[GoogleCredentials]:
        """
        Gets the default Google credentials for a client.
        
        Args:
            client_id: The UUID of the client
            
        Returns:
            Optional[GoogleCredentials]: The default credentials or None if not found
        """
        return GoogleCredentials.query.filter_by(
            client_id=client_id,
            is_default=True
        ).first()