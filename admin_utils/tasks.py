from .provider import zet_utils as zet
from .provider import hzpp_utils as hzpp
from .models import *
from search.models import NewsEntry
import requests
import email.utils
from .provider.parse_utils import get_date_from_gtfs_static
from datetime import date, datetime
import feedparser

from zet_live.celery import app

@app.task
def update_static():
    zet_feed = StaticFeed.objects.get(provider='zet')
    hzpp_feed = StaticFeed.objects.get(provider='hzpp')
    today = date.today()

    zet_last_update = zet_feed.last_update
    hzpp_last_update = hzpp_feed.last_update

    zet_start_date = get_date_from_gtfs_static(zet.static_url, 3)

    zet_latest_version_time = email.utils.parsedate_to_datetime(requests.request('HEAD', zet.static_url).headers['Last-Modified']).replace(tzinfo=None)
    hzpp_latest_version_time = email.utils.parsedate_to_datetime(requests.request('HEAD', hzpp.static_url).headers['Last-Modified']).replace(tzinfo=None)

    if zet_latest_version_time > zet_last_update and today >= zet_start_date:
        update_zet()
        zet_feed.last_update = zet_latest_version_time
        zet_feed.save()

    if hzpp_latest_version_time > hzpp_last_update:
        update_hzpp()
        hzpp_feed.last_update = hzpp_latest_version_time
        hzpp_feed.save()


def update_zet(url=zet.static_url):
    zet.run_static_update(url)


def update_hzpp(url=hzpp.static_url):
    hzpp.run_static_update(url)


### realtime

@app.task
def sync_zet():
    zet.sync_realtime()


### news

def sync_news():
    parse_rss(zet.rss_url)


def parse_rss(url, provider=None):
    feed = feedparser.parse(url)
    date_format = '%a, %d %b %Y %H:%M:%S %z'

    NewsEntry.objects.delete()
    
    for e in feed.entries:
        new = NewsEntry(
            guid=e.id,
            link=e.link,
            title=e.title,
            description=e.description,
            date=datetime.strptime(e.published, date_format)
        )

        new.save()