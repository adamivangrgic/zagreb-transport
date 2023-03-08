import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zet_live.settings")
app = Celery("zet_live")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()