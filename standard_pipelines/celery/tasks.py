from celery import shared_task
from datetime import datetime, timedelta
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from standard_pipelines.database.models import ScheduledMixin
from standard_pipelines.data_flow.gmail_interval_followup.models import GmailIntervalFollowupSchedule
from standard_pipelines.extensions import db
from flask import current_app
from celery.signals import task_failure
import sentry_sdk

def all_subclasses(cls):
    """
    Recursively find all subclasses of a given class.
    """
    return set(cls.__subclasses__()).union(
        [sub for subclass in cls.__subclasses__() for sub in all_subclasses(subclass)]
    )

@shared_task(max_retries=3)
def run_generic_tasks(method_name: str):
    """
    Process all records of every concrete subclass of ScheduledMixin and execute the specified method on each record.
    
    When method_name == "trigger_job", only tasks that are due and within the active hours/days are processed.
    When method_name == "poll", only tasks that are not due (i.e. scheduled_time is either None or in the future)
    are processed.
    """
    now = datetime.utcnow()
    for model_class in all_subclasses(ScheduledMixin):
        # Skip abstract classes
        if getattr(model_class, '__abstract__', False):
            continue

        current_app.logger.debug(f"Checking {method_name} tasks for {model_class}")

        try:
            query = db.session.query(model_class)
            if method_name == "trigger_job":
                query = query.filter(
                    model_class.scheduled_time.isnot(None),
                    model_class.scheduled_time <= now
                )
            elif method_name == "poll":
                # Exclude tasks that are due (i.e. scheduled to be triggered now)
                query = query.filter(
                    model_class.poll_interval.isnot(None),
                    or_(
                        model_class.next_poll_time.is_(None),
                        model_class.next_poll_time > now
                    )
                )
            tasks = query.all()
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error querying tasks for {model_class}: {str(e)}")
            continue

        current_app.logger.debug(f"Found {len(tasks)} tasks for {model_class} to process with {method_name}")

        for task in tasks:
            if method_name == "trigger_job":
                # Extra in-Python check: only process tasks during active hours/days.
                if now.hour not in task.active_hours or now.weekday() not in task.active_days:
                    continue
            try:
                current_app.logger.debug(f"Enqueuing {method_name} for {task}")
                execute_task_method.delay(task.__class__.__name__, task.id, method_name)
            except Exception as e:
                current_app.logger.error(f"Error enqueuing {method_name} for {task}: {str(e)}")

@shared_task
def execute_task_method(model_class_name: str, task_id: str, method_name: str):
    model_class = None
    for subclass in all_subclasses(ScheduledMixin):
        if subclass.__name__ == model_class_name:
            model_class = subclass
            break

    if model_class is None:
        current_app.logger.error(f"Model class {model_class_name} not found.")
        return

    task_instance = db.session.query(model_class).get(task_id)
    if not task_instance:
        current_app.logger.error(f"Task with id {task_id} not found in {model_class_name}.")
        return

    try:
        ALLOWED_METHODS = ['trigger_job', 'execute_poll']
        if method_name not in ALLOWED_METHODS:
            current_app.logger.error(f"Invalid method name {method_name}")
            return
        method = getattr(task_instance, method_name, None)
        if callable(method):
            current_app.logger.debug(f"Executing {method_name} for {task_instance}")
            method()
        else:
            current_app.logger.error(f"Method {method_name} is not callable on {task_instance}")
    except Exception as e:
        # TODO: Add sentry capture here
        # Also include db.rollback()
        sentry_sdk.capture_exception(e)
        db.session.rollback()
        current_app.logger.error(f"Error executing {method_name} on {task_instance}: {str(e)}")

@task_failure.connect
def handle_task_failure(task_id, exception, args, kwargs, traceback, einfo, **kw):
    # Always rollback any db changes
    db.session.rollback()
    
    # Log the error
    current_app.logger.error(f"Celery task {task_id} failed: {str(exception)}")
    
    # Send to Sentry (Sentry integration should be configured for Celery)
    sentry_sdk.capture_exception(exception)