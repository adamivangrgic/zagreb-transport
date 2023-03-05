import os
from celery import Celery

from datetime import timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_celery.settings")
app = Celery("zet_live")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'run-sync-every-20-sec': {
        'task': 'admin_utils.tasks.sync_zet',
        'schedule': timedelta(seconds=20),
    },
}