from celery import shared_task
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from standard_pipelines.database.models import ScheduledMixin
from standard_pipelines.data_flow.gmail_interval_followup.models import GmailIntervalFollowupSchedule
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
    from standard_pipelines.data_flow.gmail_interval_followup.models import GmailIntervalFollowupSchedule
    
    current_app.logger.debug('Checking for scheduled tasks')
    now = datetime.utcnow()

    # Loop over every concrete subclass of ScheduledMixin
    for model_class in all_subclasses(ScheduledMixin):
        current_app.logger.debug(f'Checking for due tasks for {model_class}')
        # Skip abstract classes
        if getattr(model_class, '__abstract__', False):
            continue
        current_app.logger.debug(f'Checking for due tasks for {model_class}')
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
                if now.hour in task.active_hours and now.weekday() in task.active_days:
                    current_app.logger.debug(f"Triggering job for {task}")
                    # Instead of task.trigger_job.delay(), call the wrapper task.
                    trigger_job_task.delay(task.__class__.__name__, task.id)
            except Exception as e:
                current_app.logger.error(f"Error running task {task}: {str(e)}")


@shared_task
def trigger_job_task(model_class_name: str, task_id: str):
    # Retrieve the correct model class by searching the ScheduledMixin subclasses.
    model_class = None
    for subclass in all_subclasses(ScheduledMixin):
        if subclass.__name__ == model_class_name:
            model_class = subclass
            break

    if model_class is None:
        current_app.logger.error(f"Model class {model_class_name} not found.")
        return

    # Retrieve the instance from the database using its ID.
    task_instance = db.session.query(model_class).get(task_id)
    if not task_instance:
        current_app.logger.error(f"Task with id {task_id} not found in {model_class_name}.")
        return

    # Now call the instance’s trigger_job (which is a normal method)
    try:
        current_app.logger.debug(f"Triggering job for {task_instance}")
        task_instance.trigger_job()
    except Exception as e:
        current_app.logger.error(f"Error running task {task_instance}: {str(e)}")