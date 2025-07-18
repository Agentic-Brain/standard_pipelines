import pytest
from datetime import datetime, timedelta, timezone
from standard_pipelines.database.models import ScheduledMixin
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from standard_pipelines.extensions import db
from freezegun import freeze_time
from pprint import pp

class TestScheduledModel(ScheduledMixin):
    __tablename__ = 'test_scheduled_model'
    __abstract__ = False
    name: Mapped[str] = mapped_column(String, nullable=False)
    
    
    def trigger_job(self) -> None:
        self.scheduled_time = datetime.utcnow() + timedelta(minutes=self.recurrence_interval) # type: ignore
        print(f"Scheduled time set to {self.scheduled_time}")

def test_basic_scheduling(frozen_datetime):
    model = TestScheduledModel(name="test") # type: ignore
    model.set_scheduled_time_to_now()
    model.save()
    
    assert model.scheduled_time == datetime.utcnow()
    assert model.run_count == 0
    assert model.max_runs is None

def test_run_count_tracking() -> None:
    model = TestScheduledModel(name="test") # type: ignore
    model.save()
    
    assert model.increment_run_count() is True
    assert model.run_count == 1
    
    model.max_runs = 2
    assert model.increment_run_count() is False
    assert model.run_count == 2
    
    assert model.increment_run_count() is False
    assert model.run_count == 3
    assert model.scheduled_time is None


def test_active_hours_validation():
    model = TestScheduledModel(name="test") # type: ignore
    
    with pytest.raises(ValueError, match="Must specify at least one active hour"):
        model.set_active_hours([])
    
    with pytest.raises(ValueError, match="Hours must be between 0 and 23"):
        model.set_active_hours([24])
    
    with pytest.raises(ValueError, match="Duplicate hours are not allowed"):
        model.set_active_hours([1, 1])
    
    model.set_active_hours([9, 10, 11])
    assert model.active_hours == [9, 10, 11]

def test_active_days_validation():
    model = TestScheduledModel(name="test") # type: ignore
    
    with pytest.raises(ValueError, match="Must specify at least one active day"):
        model.set_active_days([])
    
    with pytest.raises(ValueError, match="Days must be between 0 and 6"):
        model.set_active_days([7])
    
    with pytest.raises(ValueError, match="Duplicate days are not allowed"):
        model.set_active_days([1, 1])
    
    model.set_active_days([0, 1, 2])
    assert model.active_days == [0, 1, 2]

def test_recurring_schedule(frozen_datetime) -> None:
    model = TestScheduledModel(name="test") # type: ignore
    model.set_scheduled_time_to_now()
    model.set_recurring(interval_minutes=60)
    model.save()
    
    assert model.recurrence_interval == 60
    
    # Advance time and check next schedule
    frozen_datetime.tick(delta=timedelta(minutes=120))
    model.trigger_job()
    
    # Should be scheduled 60 minutes after current time (14:00 + 60min = 15:00)
    expected_next_run = datetime.now() + timedelta(minutes=60)
    assert model.scheduled_time == expected_next_run
    
    model.disable_recurring()
    assert model.recurrence_interval is None

# TODO: Fix this test
def test_celery_task_integration(celery_app, frozen_datetime):
    pass
    # from standard_pipelines.celery.tasks import run_scheduled_tasks
    
    # model = TestScheduledModel(name="test", recurrence_interval=60)
    # model.set_scheduled_time_to_now()
    # model.max_runs = 2
    # model.save()
    # db.session.commit()  # Ensure changes are visible outside the transaction
    
    # task = run_scheduled_tasks.s()
    # task.apply().get()
    
    # assert model.run_count == 1
    # assert model.name == "triggered_1"

# TODO: Fix this test
def test_run_scheduled_tasks(frozen_datetime):
    pass
    # schedule = TestScheduledModel(name="test", recurrence_interval=60) # type: ignore
    # schedule.set_scheduled_time(datetime.now() + timedelta(minutes=1))
    # schedule.save()
    # # app.logger.debug(f"Scheduled time: {schedule.scheduled_time}")
    # run_scheduled_tasks()
    # frozen_datetime.tick(delta=timedelta(minutes=3))
    # # app.logger.debug(f'Current time: {datetime.now()}')
    # run_scheduled_tasks()
    # assert model.run_count == 1
    # assert model.name == "triggered_1"
