import os
from celery import Celery
from celery import periodic_task
from admin_utils.tasks import zet_sync

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zet_live.settings")
app = Celery("zet_live")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@periodic_task(run_every=20.0)
def run_print_message():
    zet_sync.delay()