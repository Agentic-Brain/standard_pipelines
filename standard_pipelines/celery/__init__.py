# from .config import celery_init_app
from flask import Flask
from standard_pipelines.config import DevelopmentConfig
from standard_pipelines.extensions import db
from celery import Celery, Task
import redis



def init_app(app): 
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.set_default()
    celery_app.config_from_object(app.config['CELERY_CONFIG'])
    app.extensions['celery'] = celery_app
    
    app.redis_client = redis.StrictRedis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True
    )
    return celery_app
