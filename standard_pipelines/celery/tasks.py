from celery.task import shared_task
from datetime import datetime, timedelta
from sqlalchemy import inspect
from standard_pipelines.database.scheduled_mixin import ScheduledMixin
from standard_pipelines.extensions import db

@shared_task(bind=True, max_retries=3)
def check_scheduled_items(self):
    now = datetime.utcnow()
    
    # Find all models that use ScheduledMixin
    for model in db.Model._decl_class_registry.values():
        if hasattr(model, '__bases__') and ScheduledMixin in model.__bases__:
            # Query items that are past their scheduled time and within active hours/days
            items = model.query.filter(
                model.scheduled_time <= now
            ).all()
            
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
                except Exception as e:
                    db.session.rollback()
                    self.retry(exc=e)
