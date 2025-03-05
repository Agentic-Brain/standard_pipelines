from standard_pipelines.celery.tasks import run_generic_tasks
from celery import Celery, Task
import redis
from celery.schedules import crontab

def init_app(app): 
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

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
            },         
            'run-polling-tasks-every-minute': {
                'task': 'standard_pipelines.celery.tasks.run_generic_tasks',
                'schedule': crontab(minute='*'),  # Run every minute
                'args': ('execute_poll',)
            },
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
