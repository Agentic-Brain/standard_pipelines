from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from standard_pipelines.database.models import BaseMixin
from typing import Optional
from standard_pipelines.extensions import db
from datetime import datetime


# TODO: This will need to be reformated
# directly overwrites much of the normal BaseMixin
# Will also need more descriptive name for details
class Contact(BaseMixin):
    """
    Flask-managed contacts table that mirrors data from melty.contacts
    but in a more structured format
    """
    __tablename__ = 'contacts'

    id: Mapped[int] = mapped_column(primary_key=True)
    hubspot_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    
    # Common properties extracted from the JSONB properties column
    email: Mapped[Optional[str]] = mapped_column(String)
    firstname: Mapped[Optional[str]] = mapped_column(String)
    lastname: Mapped[Optional[str]] = mapped_column(String)
    
    # Timestamps from HubSpot
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_modified_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    @property
    def full_name(self) -> str:
        """Helper method to get full name"""
        if self.firstname and self.lastname:
            return f"{self.firstname} {self.lastname}"
        return self.firstname or self.lastname or ""

    def __repr__(self) -> str:
        return f'<Contact {self.full_name}>'
