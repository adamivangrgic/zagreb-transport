import requests, zipfile
from io import BytesIO
from django.utils.dateparse import parse_date
import csv
from io import TextIOWrapper

from search.models import Stop


def download_zip(url):
    request = requests.get(url)
    return zipfile.ZipFile(BytesIO(request.content))


def date_formatter(d):
    return d[:4] + '-' + d[4:6] + '-' + d[6:]


def get_date_from_gtfs_static(url, col_num):
    file = download_zip(url)

    with file.open("feed_info.txt", mode="r") as f:
        csvreader = csv.reader(TextIOWrapper(f, 'utf-8'))
        data_line = list(csvreader)[1]

        r_date = data_line[col_num]
        f_date = date_formatter(r_date)

        return parse_date(f_date)



def set_stop_route_type(provider=None):
    if provider:
        stops = Stop.objects.filter(provider=provider)
    else:
        stops = Stop.objects.all()

    progress_sum = 0

    # Update the stop_route_type property for all the Stop objects
    updated_stops = []
    for stop in stops:
        if stop.stop_times.count() > 0:
            route_type = stop.stop_times.first().trip.route.route_type
            has_trips = True
        elif stop.stops.first().stop_times.count() > 0:
            route_type = stop.stops.first().stop_times.first().trip.route.route_type
            has_trips = False
        else:
            route_type = None
            has_trips = False
            
        updated_stops.append(Stop(pk=stop.pk, stop_route_type=route_type, has_trips=has_trips))

        if len(updated_stops) > 1300:
            Stop.objects.bulk_update(updated_stops, ['stop_route_type', 'has_trips'])
            updated_stops = []

            ###
            progress_sum += 1300
            print('set_stop_route_type - ', progress_sum / stops.count() * 100, '%')

    Stop.objects.bulk_update(updated_stops, ['stop_route_type', 'has_trips'])