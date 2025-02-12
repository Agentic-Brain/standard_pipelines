import pytest
from datetime import datetime, timedelta, timezone
from standard_pipelines.extensions import db
from standard_pipelines.database.models import ScheduledMixin
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from freezegun import freeze_time

class TestScheduledModel(ScheduledMixin):
    __tablename__ = 'test_scheduled_model'
    name: Mapped[str] = mapped_column(String, nullable=False)
    def trigger_job(self) -> bool:
        self.scheduled_time = datetime.utcnow() + timedelta(minutes=self.recurrence_interval)
        print(f"Scheduled time set to {self.scheduled_time}")

def test_basic_scheduling(frozen_datetime):
    model = TestScheduledModel(name="test") # type: ignore
    model.set_scheduled_time_to_now()
    model.save()
    
    assert model.scheduled_time == datetime.utcnow()
    assert model.run_count == 0
    assert model.max_runs is None

def test_run_count_tracking(app) -> None:
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
    assert model.is_recurring is False

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
    
    assert model.is_recurring is True
    assert model.recurrence_interval == 60
    
    # Advance time and check next schedule
    frozen_datetime.tick(delta=timedelta(minutes=120))
    model.trigger_job()
    
    # Should be scheduled 60 minutes after current time (14:00 + 60min = 15:00)
    expected_next_run = datetime.now() + timedelta(minutes=60)
    assert model.scheduled_time == expected_next_run
    
    model.disable_recurring()
    assert model.is_recurring is False
    assert model.recurrence_interval is None

# def test_celery_task_integration(celery_app, frozen_datetime):
#     from standard_pipelines.celery.tasks import check_scheduled_items
    
#     model = TestScheduledModel(name="test") # type: ignore
#     model.set_scheduled_time_to_now()
#     model.max_runs = 2
#     model.save()
    
#     task = check_scheduled_items.s()
#     task.apply().get()
    
#     assert model.run_count == 1
#     assert model.name == "triggered_1"

def test_run_scheduled_tasks(frozen_datetime, capsys, app):
    schedule = TestScheduledModel(name="test", )
    schedule.set_scheduled_time(datetime.now() + timedelta(minutes=1))
    schedule.save()
    app.logger.debug(f"Scheduled time: {schedule.scheduled_time}")
    run_scheduled_tasks()
    frozen_datetime.tick(delta=timedelta(minutes=3))
    app.logger.debug(f'Current time: {datetime.now()}')
    run_scheduled_tasks()
    # assert model.run_count == 1
    # assert model.name == "triggered_1"

#### HELPER FUNCTIONS ####from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

# Assume you have already set up Flask and SQLAlchemy (db)
db = SQLAlchemy()

# Our mixin is assumed to be imported or defined somewhere:
# from your_module import ScheduledMixin

def all_subclasses(cls):
    """
    Recursively find all subclasses of a given class.
    """
    return set(cls.__subclasses__()).union(
        [sub for subclass in cls.__subclasses__() for sub in all_subclasses(subclass)]
    )

def run_scheduled_tasks():
    """
    Check all models that inherit from ScheduledMixin and, if their scheduled time is due
    and the current day/hour is active, run their trigger_job() method.
    """
    now = datetime.utcnow()
    print('Checking tasks')

    # Loop over every concrete subclass of ScheduledMixin
    for model_class in all_subclasses(ScheduledMixin):
        # Skip abstract classes
        if getattr(model_class, '__abstract__', False):
            continue

        # Query for records where scheduled_time is set and is due
        due_tasks = db.session.query(model_class).filter(
            model_class.scheduled_time.isnot(None),
            model_class.scheduled_time <= now
        ).all()

        for task in due_tasks:
            print(f"Running task")
            # Check if current hour and day are allowed.
            # (Remember: datetime.utcnow().weekday() returns 0 for Monday, 6 for Sunday.)
            if now.hour in task.active_hours and now.weekday() in task.active_days:
                # Call the actual job trigger method.
                task.trigger_job()
                
                # Update scheduling:
                if task.is_recurring and task.recurrence_interval:
                    # Increment run count and reschedule if max_runs not reached.
                    if task.increment_run_count():
                        task.delay_scheduled_time(timedelta(minutes=task.recurrence_interval))
                    else:
                        # The task has reached its maximum number of runs.
                        pass
                else:
                    # For non-recurring tasks, clear the scheduled_time
                    task.scheduled_time = None

    # Commit all changes (for example, updated scheduled_time/run_count changes)
    # db.session.commit()
