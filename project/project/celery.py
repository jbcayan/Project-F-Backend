from __future__ import absolute_import, unicode_literals

import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab
from decouple import config

TIME_ZONE = config("TIME_ZONE")

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

app = Celery('project')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

# Celery configuration with Redis as the broker and result backend
app.conf.update(
    broker_url="redis://alibi_redis:6379",  # Broker URL for Redis
    result_backend="redis://alibi_redis:6379",  # Result backend for Redis
    task_serializer="json",  # Task serialization format
    accept_content=["json"],  # Accept only JSON content for tasks
    result_serializer="json",  # Result serialization format
    timezone=TIME_ZONE,  # Set the timezone for Celery tasks
)


app.conf.beat_schedule = {
#     "print-something-every-30-seconds": {
#         "task": "gallery.tasks.print_something", # Adjust the task path here
#         "schedule": crontab(minute="*"),  # Run every minute
#     },
    'delete-used-or-expired-otps-every-12-hours': {
        'task': 'accounts.tasks.delete_used_or_expired_otps',
        'schedule': crontab(hour=0, minute=0),
    },
    'delete-unverified-users-every-12-hours': {
        'task': 'accounts.tasks.delete_unverified_users',
        'schedule': timedelta(hours=12),
    },
}