import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zet_live.settings")
app = Celery("zet_live")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):

    # every 20 seconds
    sender.add_periodic_task(20.0, admin_utils.tasks.sync_zet())