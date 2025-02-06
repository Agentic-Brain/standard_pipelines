from celery.task import shared_task
from datetime import datetime, timedelta
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from standard_pipelines.database.scheduled_mixin import ScheduledMixin
from standard_pipelines.extensions import db
from flask import current_app

@shared_task(bind=True, max_retries=3)
def check_scheduled_items(self):
    now = datetime.utcnow()
    
    # Find all models that use ScheduledMixin
    for model in db.Model._decl_class_registry.values():
        if hasattr(model, '__class__') and isinstance(model, ScheduledMixin):
            # Query items that are past their scheduled time and within active hours/days
            items = model.query.filter(
                model.scheduled_time <= now
            ).limit(100).all()
            
            for item in items:
                if not item.is_active_time(now):
                    continue
                    
                try:
                    item.trigger_job()
                    
                    if item.is_recurring and item.recurrence_interval:
                        # Schedule next run based on the original scheduled time
                        next_time = item.scheduled_time + timedelta(minutes=item.recurrence_interval)
                        # If next time is in the past (due to delays), schedule from now
                        if next_time <= now:
                            next_time = now + timedelta(minutes=item.recurrence_interval)
                        item.scheduled_time = next_time
                    else:
                        item.scheduled_time = None
                        
                    db.session.commit()
                except SQLAlchemyError as e:
                    db.session.rollback()
                    current_app.logger.error(f'Database error in scheduled job: {str(e)}')
                    self.retry(exc=e)
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f'Unexpected error in scheduled job: {str(e)}')
                    raise
