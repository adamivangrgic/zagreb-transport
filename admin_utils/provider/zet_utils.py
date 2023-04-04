from search.models import *
from django.shortcuts import get_object_or_404
import csv
from django.utils.dateparse import parse_duration
from google.transit import gtfs_realtime_pb2  # protobuf==3.20.1, requests
import requests
from datetime import datetime, timedelta
from django.db.models import Case, When, fields, F, Q, ExpressionWrapper
from .parse_utils import set_stop_route_type, is_strictly_climbing, has_outliers_neighbour, max_outliers_neighbour #has_outliers
from io import TextIOWrapper
from django.contrib.gis.geos import Point
from itertools import groupby


static_url = "https://zet.hr/gtfs-scheduled/latest"
realtime_url = "https://zet.hr/gtfs-rt-protobuf"
provider = 'zet'


def run_static_update(url):
    file = download_zip(url)

    update_agencies(file)
    update_stops(file)
    update_routes(file)
    update_calendar_dates(file)
    update_trips(file)
    update_stops_times(file)
    update_calendar(file)


def update_agencies(file):
    Agency.objects.filter(provider=provider).delete()

    with file.open("agency.txt", mode="r") as f:
        csvreader = csv.reader(TextIOWrapper(f, 'utf-8'))
        next(csvreader)

        bulk_list = []

        for data in csvreader:

            new_agency = Agency(
                agency_id=data[0],
                agency_name=data[1],
                agency_url=data[2],
                agency_phone=data[5],
                agency_fare_url=data[6],
                provider=provider
            )

            bulk_list.append(new_agency)
            if len(bulk_list) > 5000:
                Agency.objects.bulk_create(bulk_list)
                bulk_list = []

        Agency.objects.bulk_create(bulk_list)


def update_stops(file):
    Stop.objects.filter(provider=provider).delete()

    # stations
    with file.open("stops.txt", mode="r") as f:
        csvreader = csv.reader(TextIOWrapper(f, 'utf-8'))
        next(csvreader)

        bulk_list = []

        for data in csvreader:
            if int(data[8]) == 1:
                new_stop = Stop(
                    stop_id=data[0],
                    stop_code=data[1],
                    stop_name=data[2],
                    stop_loc = Point(float(data[4]), float(data[5])),
                    location_type=data[8],
                    provider=provider
                )

                bulk_list.append(new_stop)
                if len(bulk_list) > 5000:
                    Stop.objects.bulk_create(bulk_list)
                    bulk_list = []

        Stop.objects.bulk_create(bulk_list)

    # stops
    with file.open("stops.txt", mode="r") as f:
        csvreader = csv.reader(TextIOWrapper(f, 'utf-8'))
        next(csvreader)

        bulk_list = []

        for data in csvreader:

            if int(data[8]) == 0:
                parent = get_object_or_404(Stop, stop_id=data[9])

                new_stop = Stop(
                    stop_id=data[0],
                    stop_code=data[1],
                    stop_name=data[2],
                    parent_station=parent,
                    stop_loc=Point(float(data[4]), float(data[5])),
                    location_type=data[8],
                    provider=provider
                )

                bulk_list.append(new_stop)
                if len(bulk_list) > 5000:
                    Stop.objects.bulk_create(bulk_list)
                    bulk_list = []

        Stop.objects.bulk_create(bulk_list)


def update_routes(file):
    Route.objects.filter(provider=provider).delete()

    with file.open("routes.txt", mode="r") as f:
        csvreader = csv.reader(TextIOWrapper(f, 'utf-8'))
        next(csvreader)

        bulk_list = []

        agencies = {agency.agency_id: agency for agency in Agency.objects.all()}

        for data in csvreader:

            agency = agencies.get(data[1])

            new_route = Route(
                route_id=data[0],
                route_short_name=data[2],
                route_long_name=data[3],
                route_type=data[5],
                route_color=data[7],
                route_text_color=data[8],
                agency=agency,
                provider=provider
            )

            bulk_list.append(new_route)
            if len(bulk_list) > 5000:
                Route.objects.bulk_create(bulk_list)
                bulk_list = []

        Route.objects.bulk_create(bulk_list)


def update_calendar_dates(file):
    CalendarDate.objects.filter(provider=provider).delete()

    with file.open("calendar_dates.txt", mode="r") as f:
        csvreader = csv.reader(TextIOWrapper(f, 'utf-8'))
        next(csvreader)

        bulk_list = []

        for data in csvreader:
            new_cd = CalendarDate(
                service_id=data[0],
                date=date_formatter(data[1]),
                exception_type=data[2],
                provider=provider
            )

            bulk_list.append(new_cd)
            if len(bulk_list) > 5000:
                Trip.objects.bulk_create(bulk_list)
                bulk_list = []

        CalendarDate.objects.bulk_create(bulk_list)


def update_trips(file):
    Trip.objects.filter(provider=provider).delete()

    with file.open("trips.txt", mode="r") as f:
        csvreader = csv.reader(TextIOWrapper(f, 'utf-8'))
        next(csvreader)

        bulk_list = []

        routes = {route.route_id: route for route in Route.objects.all()}

        for data in csvreader:

            route = routes.get(data[0])

            new_trip = Trip(
                trip_id=data[2],
                trip_headsign=data[3],
                route=route,
                service_id=data[1],
                block_id=data[6],
                provider=provider
            )

            bulk_list.append(new_trip)
            if len(bulk_list) > 5000:
                Trip.objects.bulk_create(bulk_list)
                bulk_list = []

        Trip.objects.bulk_create(bulk_list)


def update_stops_times(file):
    StopTime.objects.filter(provider=provider).delete()

    with file.open("stop_times.txt", mode="r") as f:
        csvreader = csv.reader(TextIOWrapper(f, 'utf-8'))
        next(csvreader)

        bulk_list = []

        trips = {trip.trip_id: trip for trip in Trip.objects.all()}
        stops = {stop.stop_id: stop for stop in Stop.objects.all()}

        progress_sum = 0

        for data in csvreader:

            trip = trips.get(data[0])
            stop = stops.get(data[3])

            new_stop_time = StopTime(
                trip=trip,
                arrival_time=parse_duration(data[1]),
                departure_time=parse_duration(data[2]),
                stop=stop,
                stop_sequence=data[4],
                provider=provider
            )

            bulk_list.append(new_stop_time)
            if len(bulk_list) > 5000:
                StopTime.objects.bulk_create(bulk_list)
                bulk_list = []

                ###
                progress_sum += 5000
                print('update_stop_times - ' + provider, progress_sum / 1500000 * 100, '%')

        StopTime.objects.bulk_create(bulk_list)

    set_stop_route_type(provider)


def update_calendar(file):
    Calendar.objects.filter(provider=provider).delete()

    with file.open("calendar.txt", mode="r") as f:
        csvreader = csv.reader(TextIOWrapper(f, 'utf-8'))
        next(csvreader)

        bulk_list = []

        for data in csvreader:

            new_cal = Calendar(
                service_id=data[0],
                monday=data[1],
                tuesday=data[2],
                wednesday=data[3],
                thursday=data[4],
                friday=data[5],
                saturday=data[6],
                sunday=data[7],
                start_date=date_formatter(data[8]),
                end_date=date_formatter(data[9]),
                provider=provider
            )

            bulk_list.append(new_cal)
            if len(bulk_list) > 5000:
                Calendar.objects.bulk_create(bulk_list)
                bulk_list = []

        Calendar.objects.bulk_create(bulk_list)


def sync_realtime():
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(realtime_url)
    feed.ParseFromString(response.content)

    current_time = datetime.now()
    today_mid = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    if current_time.time().hour < 5:
        today_mid = today_mid - timedelta(days=1)

    delays = {}
    # abn_delays = {}
    awaiting_departure = []

    for entity in feed.entity:
        # if abs(entity.trip_update.stop_time_update[-1].arrival.delay) < 10 * 60 and entity.trip_update.stop_time_update[-1].departure.time > 0:  # delay up to 10 min
        #     delays[entity.trip_update.trip.trip_id] = timedelta(seconds=entity.trip_update.stop_time_update[-1].arrival.delay)

        # elif entity.trip_update.stop_time_update[-1].departure.time > 0:  # abnormal delay
        #     abn_delays[entity.trip_update.trip.trip_id] = timedelta(seconds=entity.trip_update.stop_time_update[-1].arrival.delay)

        if entity.trip_update.stop_time_update[-1].departure.time > 0:
            delays[entity.trip_update.trip.trip_id] = timedelta(seconds=entity.trip_update.stop_time_update[-1].arrival.delay)

        elif entity.trip_update.stop_time_update[-1].stop_sequence == 1:  # waiting to depart
            awaiting_departure.append(entity.trip_update.trip.trip_id)

    stop_times = StopTime.objects \
        .filter(trip__trip_id__in=delays.keys()) \
        .annotate(delay_an=Case(*[When(trip__trip_id=t, then=delays[t]) for t in delays], output_field=fields.DurationField())) \
        .annotate(departure_time_an=ExpressionWrapper(F('departure_time') + F('delay_an') + today_mid, output_field=fields.DateTimeField())) \
        .filter(Q(departure_time_an__gt=current_time - timedelta(seconds=30)) |
            ( Q(departure_time_an__lte=current_time - timedelta(seconds=30))
            & ( Q(updated_at__lt=current_time - timedelta(hours=23)) | Q(delay_departure=timedelta(0)) ) ))
        # .filter(departure_time_an__gt=current_time - timedelta(minutes=3))
    stop_times.update(updated_at=current_time, delay_departure=F('delay_an'), delay_arrival=F('delay_an'))

    stops_waiting = StopTime.objects.filter(trip__trip_id__in=awaiting_departure)
    stops_waiting.update(wait_updated_at=current_time, delay_departure=timedelta(), delay_arrival=timedelta())
    # stops_waiting.update(wait_updated_at=current_time)

    #### integrity check

    detected_trips_ids = []

    trips_ch = Trip.objects.filter(Q(checked_integrity_at__lte=current_time - timedelta(minutes=3)) & Q(trip_id__in=delays.keys())) #
    stop_times_ch = StopTime.objects.filter(trip__in=trips_ch).values('delay_departure', 'departure_time', 'trip__trip_id', 'stop_sequence')

    stoptime_timelines = {}
    for trip_id, stop_times in groupby(stop_times_ch, key=lambda x: x['trip__trip_id']):
        stoptime_timelines[trip_id] = sorted(list(stop_times), key=lambda d: d['stop_sequence']) 

    for trip_id in stoptime_timelines:
        values = stoptime_timelines[trip_id]

        delay_list = []
        departure_time_list = []

        for val in values:
            delay_list.append((val['delay_departure']).total_seconds())
            departure_time_list.append((val['delay_departure'] + val['departure_time']).total_seconds())

        if (not is_strictly_climbing(departure_time_list)) or has_outliers_neighbour(delay_list, 102):# or has_outliers(delay_list)
            detected_trips_ids.append(trip_id)

            #print('{} / {}'.format(trip_id, max_outliers_neighbour(delay_list)))

    trips_ch.update(checked_integrity_at=current_time)

    #### working with detected trips

    detected_stop_times = StopTime.objects \
        .filter(trip__trip_id__in=detected_trips_ids) \
        .annotate(delay_an=Case(*[When(trip__trip_id=t, then=delays[t]) for t in delays], output_field=fields.DurationField()))
    detected_stop_times.update(updated_at=current_time, delay_departure=F('delay_an'), delay_arrival=F('delay_an'))


    #print(detected_trips_ids) #datetime.now() - current_time