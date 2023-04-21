from .provider import zet_utils as zet
from .provider import hzpp_utils as hzpp
from .models import *
from search.models import NewsEntry
import requests
import email.utils
from .provider.parse_utils import get_date_from_gtfs_static
from datetime import date, datetime
import feedparser
import re
from bs4 import BeautifulSoup

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

@app.task
def sync_news():
    NewsEntry.objects.all().delete()

    parse_rss(zet.rss_url)
    parse_html('https://holdingcentar.zgh.hr/', 'div.alert-item.grupa_5631 > div.alert-text > div')


def parse_rss(url, provider=None):
    feed = feedparser.parse(url)
    date_format = '%a, %d %b %Y %H:%M:%S %z'
    
    for e in feed.entries:
        description = e.description

        pattern = re.compile('<.*?>')
        description_text = re.sub(pattern, '', description)

        new = NewsEntry(
            guid=e.id,
            link=e.link,
            title=e.title,
            description=description,
            description_text=description_text,
            date=datetime.strptime(e.published, date_format)
        )

        new.save()

def parse_html(url, bs4_instruction, provider=None):
    response = requests.get(url)
    html_content = response.content
    soup = BeautifulSoup(html_content, 'html.parser')
    elements = soup.select()

    text_content = elements[0].get_text()
    html_content = elements[0].prettify()

    new = NewsEntry(
        guid=url,
        link=url,
        title=text_content[:50],
        description=html_content,
        description_text=text_content,
        date=datetime.now()
    )

    new.save()