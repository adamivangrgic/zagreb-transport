import os
from celery import Celery
from celery.task import periodic_task
from admin_utils.tasks import zet_sync

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zet_live.settings")
app = Celery("zet_live")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()