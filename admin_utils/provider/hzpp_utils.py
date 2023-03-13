# import os
# from zet_live.settings import BASE_DIR
from search.models import *
# from django.shortcuts import get_object_or_404
import csv
from django.utils.dateparse import parse_duration
# from google.transit import gtfs_realtime_pb2  # protobuf==3.20.1, requests
# import requests
# from datetime import datetime, timedelta
# from django.db.models import Case, When, fields, Q, F, ExpressionWrapper
from .parse_utils import download_zip, date_formatter
from io import TextIOWrapper


static_url = "http://www.hzpp.hr/Media/Default/GTFS/GTFS_files.zip"
# realtime_url = ""
provider = 'hzpp'


def run_static_update(url):
    file = download_zip(url)

    update_agencies(file)
    update_stops(file)
    update_routes(file)
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
                agency_email=data[6],
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
            new_station = Stop(
                stop_id=data[0],
                stop_name=data[1],
                stop_loc = [data[2], data[3]],
                location_type=1,
                provider=provider
            )

            bulk_list.append(new_station)
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
                agency=agency,
                provider=provider
            )

            bulk_list.append(new_route)
            if len(bulk_list) > 5000:
                Route.objects.bulk_create(bulk_list)
                bulk_list = []

        Route.objects.bulk_create(bulk_list)


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
                trip_short_name=data[4],
                route=route,
                service_id=data[1],
                bikes_allowed=data[8],
                wheelchair_accessible=data[9],
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
                print(progress_sum / 600000 * 100, '%')

        StopTime.objects.bulk_create(bulk_list)


def update_calendar(file):
    Calendar.objects.filter(provider=provider).delete()

    with file.open("calendar.txt", mode="r") as f:
        csvreader = csv.reader(TextIOWrapper(f, 'utf-8'))
        next(csvreader)

        bulk_list = []

        for data in csvreader:

            new_cal = Calendar(
                service_id=data[0],
                monday=data[3],
                tuesday=data[4],
                wednesday=data[5],
                thursday=data[6],
                friday=data[7],
                saturday=data[8],
                sunday=data[9],
                start_date=date_formatter(data[1]),
                end_date=date_formatter(data[2]),
                provider=provider
            )

            bulk_list.append(new_cal)
            if len(bulk_list) > 5000:
                Calendar.objects.bulk_create(bulk_list)
                bulk_list = []

        Calendar.objects.bulk_create(bulk_list)
