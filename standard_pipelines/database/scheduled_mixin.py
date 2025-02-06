from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from standard_pipelines.database.models import BaseMixin

class ScheduledMixin(BaseMixin, ABC):
    __abstract__ = True

    scheduled_time: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True, index=True)
    active_hours: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True, default=list(range(24)))
    active_days: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True, default=list(range(7)))
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recurrence_interval: Mapped[Optional[int]] = mapped_column(JSON, nullable=True)

    @abstractmethod
    def trigger_job(self) -> None:
        """Abstract method that must be implemented to trigger the actual job."""
        pass

    def set_scheduled_time_to_now(self) -> None:
        self.scheduled_time = datetime.utcnow()

    def delay_scheduled_time(self, delay: timedelta) -> None:
        if self.scheduled_time is None:
            self.scheduled_time = datetime.utcnow()
        self.scheduled_time += delay

    def set_scheduled_time(self, new_time: datetime) -> None:
        if new_time < datetime.utcnow():
            raise ValueError("Cannot schedule time in the past")
        self.scheduled_time = new_time

    def set_active_hours(self, hours: List[int]) -> None:
        if not hours:
            raise ValueError("Must specify at least one active hour")
        if not all(0 <= h <= 23 for h in hours):
            raise ValueError("Hours must be between 0 and 23")
        if len(set(hours)) != len(hours):
            raise ValueError("Duplicate hours are not allowed")
        self.active_hours = sorted(hours)

    def set_active_days(self, days: List[int]) -> None:
        if not days:
            raise ValueError("Must specify at least one active day")
        if not all(0 <= d <= 6 for d in days):
            raise ValueError("Days must be between 0 and 6 (Monday-Sunday)")
        if len(set(days)) != len(days):
            raise ValueError("Duplicate days are not allowed")
        self.active_days = sorted(days)

    def set_recurring(self, interval_minutes: int) -> None:
        if interval_minutes < 1:
            raise ValueError("Recurrence interval must be at least 1 minute")
        self.is_recurring = True
        self.recurrence_interval = interval_minutes

    def disable_recurring(self) -> None:
        self.is_recurring = False
        self.recurrence_interval = None

    def is_active_time(self, check_time: Optional[datetime] = None) -> bool:
        if check_time is None:
            check_time = datetime.utcnow()
        return (check_time.hour in self.active_hours and 
                check_time.weekday() in self.active_days)
