from .provider import zet_utils as zet
from .provider import hzpp_utils as hzpp
from .models import *
import requests
import email.utils

def update_static():
    zet_feed = StaticFeed.objects.get(provider='zet')
    hzpp_feed = StaticFeed.objects.get(provider='hzpp')

    zet_last_update = zet_feed.last_update
    hzpp_last_update = hzpp_feed.last_update

    zet_latest_version_time = email.utils.parsedate_to_datetime(requests.request('HEAD', "https://zet.hr/gtfs-scheduled/latest").headers['Last-Modified'])
    hzpp_latest_version_time = email.utils.parsedate_to_datetime(requests.request('HEAD', "http://www.hzpp.hr/Media/Default/GTFS/GTFS_files.zip").headers['Last-Modified'])

    if zet_latest_version_time > zet_last_update:
        update_zet()
        zet_feed.last_update = zet_latest_version_time
        zet_feed.save()

    if hzpp_latest_version_time > hzpp_last_update:
        update_hzpp()
        hzpp_feed.last_update = hzpp_latest_version_time
        hzpp_feed.save()


def update_zet():
    zet.run_static_update()


def update_hzpp():
    hzpp.run_static_update()


def sync(a):
    while True:
        zet.sync_realtime()
        time.sleep(20)