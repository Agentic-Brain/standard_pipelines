from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from standard_pipelines.database.models import BaseMixin


class Conversation(BaseMixin):
    __tablename__ = "conversation"

    thread_id: Mapped[str] = mapped_column(String(512))
    openai_thread_id: Mapped[str] = mapped_column(String(512))
    chat_service: Mapped[str] = mapped_column(String(20))

    def __repr__(self):
        return f"<Conversation {self.chat_service} - {self.thread_id} - {self.openai_thread_id}>"