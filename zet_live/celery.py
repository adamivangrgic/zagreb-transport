import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zet_live.settings")
app = Celery("zet_live")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'zet sync every 20 sec': {
        'task': 'admin_utils.tasks.sync_zet',
        'schedule': 20
    },

    'update static files': {
        'task': 'admin_utils.tasks.update_static',
        'schedule': crontab(hour=3, minute=30)
    },
}