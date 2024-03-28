FROM python:3.9.7
ENV PYTHONUNBUFFERED 1

WORKDIR /code

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
        build-essential \
        python3-gdal

COPY requirements.txt /code/
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY . /code/
