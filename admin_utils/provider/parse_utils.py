import requests, zipfile
from io import BytesIO

from search.models import Stop


def download_zip(url):
    request = requests.get(url)
    return zipfile.ZipFile(BytesIO(request.content))


def date_formatter(d):
    return d[:4] + '-' + d[4:6] + '-' + d[6:]


def set_stop_route_type(provider=None):
    if provider:
        stops = Stop.objects.filter(provider)
    else:
        stops = Stop.objects.all()

    progress_sum = 0

    # Update the stop_route_type property for all the Stop objects
    updated_stops = []
    for stop in stops:
        if stop.stop_times.count() > 0:
            route_type = stop.stop_times.first().trip.route.route_type
            hasTrips = True
        elif stop.stops.first().stop_times.count() > 0:
            route_type = stop.stops.first().stop_times.first().trip.route.route_type
            hasTrips = False
        else:
            route_type = None
            hasTrips = False
            
        updated_stops.append(Stop(pk=stop.pk, stop_route_type=route_type, hasTrips=hasTrips))

        if len(updated_stops) > 500:
            Stop.objects.bulk_update(updated_stops, ['stop_route_type', 'hasTrips'])
            updated_stops = []

            ###
            progress_sum += 500
            print(progress_sum / stops.count() * 100, '%')

    Stop.objects.bulk_update(updated_stops, ['stop_route_type', 'hasTrips'])