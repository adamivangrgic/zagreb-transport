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
    try: update_zet()
    except Exception as e: print(e)
    
    try: update_hzpp()
    except Exception as e: print(e)


def update_zet(url=zet.static_url):
    zet_feed = StaticFeed.objects.get(provider='zet')
    zet_last_update = zet_feed.last_update
    zet_start_date = get_date_from_gtfs_static(zet.static_url, 3)
    zet_latest_version_time = email.utils.parsedate_to_datetime(requests.request('HEAD', zet.static_url).headers['Last-Modified']).replace(tzinfo=None)

    if zet_latest_version_time > zet_last_update and date.today() >= zet_start_date:
        zet.run_static_update(url)
        zet_feed.last_update = zet_latest_version_time
        zet_feed.save()


def update_hzpp(url=hzpp.static_url):
    hzpp_feed = StaticFeed.objects.get(provider='hzpp')
    hzpp_last_update = hzpp_feed.last_update
    hzpp_latest_version_time = email.utils.parsedate_to_datetime(requests.request('HEAD', hzpp.static_url).headers['Last-Modified']).replace(tzinfo=None)

    if hzpp_latest_version_time > hzpp_last_update:
        hzpp.run_static_update(url)
        hzpp_feed.last_update = hzpp_latest_version_time
        hzpp_feed.save()


### realtime

@app.task
def sync_zet():
    zet.sync_realtime()


### news

@app.task
def sync_news():
    NewsEntry.objects.all().delete()

    parse_html('https://holdingcentar.zgh.hr/', 'div.alert-item.grupa_5631 > div.alert-text > p', guid='zet_stanje')
    parse_rss(zet.rss_url)
    parse_html('https://www.hzpp.hr/stanje-u-prometu-2', 'div.article-item.full', guid='hzpp_stanje', title='HŽPP izmjene u prometu')


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

def parse_html(url, bs4_instruction, provider=None, title=None, guid=None):
    response = requests.get(url)
    html_content = response.content
    soup = BeautifulSoup(html_content, 'html.parser')
    elements = soup.select(bs4_instruction)

    text_content = elements[0].get_text()
    html_content = elements[0].prettify()

    new = NewsEntry(
        guid=guid if guid else url,
        link=url,
        title=title if title else ' '.join(text_content.split(' ')[:8]),
        description=html_content,
        description_text=text_content,
        date=datetime.now()
    )

    new.save()