from standard_pipelines.celery.tasks import run_generic_tasks
from celery import Celery, Task
import redis
from celery.schedules import crontab
import traceback
import sentry_sdk
from standard_pipelines.extensions import db

def init_app(app): 
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                try:
                    return self.run(*args, **kwargs)
                except Exception as e:
                    # Log the error using the Flask app's logger
                    app.logger.error(f"Celery task error in {self.name}: {str(e)}")
                    if app.config.get('FLASK_ENV') == 'development':
                        app.logger.error(traceback.format_exc())
                    
                    # Send to Sentry (will happen automatically if you have the Celery integration)
                    # But we can add extra context if needed
                    # TODO: Change this context and use the following line instead
                    # sentry_sdk.capture_exception(e)
                    sentry_sdk.set_context("task", {
                        "task_id": self.request.id,
                        "task_name": self.name,
                        "args": args,
                        "kwargs": kwargs
                    })
                    
                    db.session.rollback()
                    
                    # Re-raise the exception for Celery to handle the task state
                    raise

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.set_default()
    
    # Add beat schedule configuration
    app.config.setdefault('CELERY_CONFIG', {})
    app.config['CELERY_CONFIG'].update(
        beat_schedule={
            'run-scheduled-tasks-every-minute': {
                'task': 'standard_pipelines.celery.tasks.run_generic_tasks',
                'schedule': crontab(minute='*'),  # Run every minute
                'args': ('trigger_job',)
            }         
            # 'run-polling-tasks-every-minute': {
            #     'task': 'standard_pipelines.celery.tasks.run_generic_tasks',
            #     'schedule': crontab(minute='*'),  # Run every minute
            #     'args': ('execute_poll',)
            # },
        }
    )
    
    celery_app.config_from_object(app.config['CELERY_CONFIG'])
    app.extensions['celery'] = celery_app
    
    app.redis_client = redis.StrictRedis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True
    )
    return celery_app
