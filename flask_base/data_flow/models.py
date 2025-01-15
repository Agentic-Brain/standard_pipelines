from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from flask_base.database.models import BaseMixin

class Notification(BaseMixin):
    """Model for storing notifications with title and body for consumption by apprise."""
    __tablename__ = 'notifications'
    
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def __repr__(self):
        return f'<Notification {self.title}>'