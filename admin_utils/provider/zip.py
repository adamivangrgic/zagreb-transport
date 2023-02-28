import requests, zipfile
from io import BytesIO


def download_zip(url):
    request = requests.get(url)
    return zipfile.ZipFile(BytesIO(request.content))