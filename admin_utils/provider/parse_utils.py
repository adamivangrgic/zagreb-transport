import requests, zipfile
from io import BytesIO


def download_zip(url):
    request = requests.get(url)
    return zipfile.ZipFile(BytesIO(request.content))


def date_formatter(d):
    return d[:4] + '-' + d[4:6] + '-' + d[6:]