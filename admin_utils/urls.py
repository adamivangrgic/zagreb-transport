from django.urls import path

from . import tasks

urlpatterns = [
    path('update_static/', tasks.update_static, name='update_static'),
    path('sync_zet/', tasks.sync_zet, name='sync_zet'),
    path('sync_news/', tasks.sync_news, name='sync_news'),
]