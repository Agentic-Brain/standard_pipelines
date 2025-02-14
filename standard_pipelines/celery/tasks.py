from celery import shared_task
from datetime import datetime, timedelta
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from standard_pipelines.database.models import ScheduledMixin
from standard_pipelines.extensions import db
from flask import current_app


def all_subclasses(cls):
    """
    Recursively find all subclasses of a given class.
    """
    return set(cls.__subclasses__()).union(
        [sub for subclass in cls.__subclasses__() for sub in all_subclasses(subclass)]
    )

@shared_task(max_retries=3)
def run_scheduled_tasks():
    """
    Check all models that inherit from ScheduledMixin and, if their scheduled time is due
    and the current day/hour is active, run their trigger_job() method.
    """
    now = datetime.utcnow()

    # Loop over every concrete subclass of ScheduledMixin
    for model_class in all_subclasses(ScheduledMixin):
        # Skip abstract classes
        if getattr(model_class, '__abstract__', False):
            continue
        # Query for records where scheduled_time is set and is due
        try:
            due_tasks = db.session.query(model_class).filter(
                model_class.scheduled_time.isnot(None),
                model_class.scheduled_time <= now
            ).all()
        
        except SQLAlchemyError as e:
            current_app.logger.error(f'Error querying due tasks for {model_class}: {str(e)}')
            continue
        
        if due_tasks:
            current_app.logger.debug(f'Found {len(due_tasks)} due tasks for {model_class}')
        else:
            current_app.logger.debug(f'No due tasks found for {model_class}')

        current_app.logger.info(f'Due tasks: {due_tasks}')
        for task in due_tasks:
            try:
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
            except Exception as e:
                current_app.logger.error(f'Error running task {task}: {str(e)}')
