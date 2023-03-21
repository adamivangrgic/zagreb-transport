from django.shortcuts import render
from .models import *
from django.http import JsonResponse
from datetime import datetime
from django.db.models import Q, F, ExpressionWrapper, fields, Subquery, OuterRef, Case, When, IntegerField
from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.db.models.functions import Distance


def index(request):
    saved_stops = request.COOKIES.get('saved_stops')

    if not saved_stops:
        saved_stops = []
    else:
        saved_stops = saved_stops.split('|')

    current_time = datetime.now()
    today_mid = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    if current_time.time().hour < 5:
        today_mid = today_mid - timedelta(days=1)

    data = {}

    for stop_id in saved_stops:
        stop = Stop.objects.get(stop_id=stop_id)
        f_stimes = get_stop_times(stop, today_mid, 4, -0.5, current_time)
        headsigns = Trip.objects.filter(stop_times__in=f_stimes).distinct().values_list('trip_headsign', flat=True)

        data[stop.stop_id] = {'hs': ', '.join(headsigns), 'stimes': f_stimes, 'stop_code': stop.stop_code,
                              'station_name': stop.stop_name}

    # map_stations = Stop.objects.filter(Q(location_type=1))

    return render(request, 'search/map.html', {'stops': data})


def map(request):
    return render(request, 'search/map.html')


def search_suggestions(request):
    query = request.GET.get('q')

    output = [[], [], []]  # rail 0, tram 1, bus 2

    if len(query) > 2:
        stations = Stop.objects.filter(Q(stop_name__icontains=query) & Q(location_type=1)) # stop_name__unaccent__lower__trigram_similar

        for station in stations:
            route_type = station.stop_route_type

            if route_type == 2:  # rail
                output[0].append([station.stop_name, station.stop_id])

            elif route_type == 0:  # tram
                output[1].append([station.stop_name, station.stop_id])

            elif route_type == 3:  # bus
                output[2].append([station.stop_name, station.stop_id])

    return JsonResponse({'status': 200, 'data': output})


def location_search(request):
    sw_lon = float(request.GET.get('sw_lon', 0))
    sw_lat = float(request.GET.get('sw_lat', 0))
    ne_lon = float(request.GET.get('ne_lon', 0))
    ne_lat = float(request.GET.get('ne_lat', 0))
    zoom = float(request.GET.get('zoom', 0))

    stops = get_stops_bbox(sw_lon, sw_lat, ne_lon, ne_lat)

    order_priority = Case(
        When(stop_route_type=2, then=0),
        When(stop_route_type=0, then=1),
        When(stop_route_type=3, then=2),
        default=3,  # handle other priorities
        output_field=IntegerField(),
    )

    if zoom >= 17:
        stops = stops.exclude(stop_times__isnull=True).order_by(order_priority)[:150]
    elif zoom <= 11:
        stops = stops.filter(stop_route_type=2).order_by(order_priority)[:150]
    else:
        stops = stops.filter(location_type=1).order_by(order_priority)[:150]

    data = []

    for stop in stops:
        data.append({'lat': stop.stop_loc.x, 'lon': stop.stop_loc.y, 'id': stop.stop_id, 'name': stop.stop_name, 'type': stop.stop_route_type})

    return JsonResponse({'status': 200, 'data': data})


# def get_stops_radius(lat, lon, radius):
#     point = Point(lat, lon)
#     return Stop.objects.filter(stop_loc__distance_lt=(point, radius))


def get_stops_bbox(sw_lon, sw_lat, ne_lon, ne_lat):
    polygon = Polygon.from_bbox((sw_lat, sw_lon, ne_lat, ne_lon))
    return Stop.objects.filter(stop_loc__within=polygon)


def get_service_ids(date):
    service = CalendarDate.objects.filter(date=date)
    service_ids = list(service.values_list('service_id', flat=True))

    if date.weekday() == 0:
        weekday_filter = Q(monday=1)
    elif date.weekday() == 1:
        weekday_filter = Q(tuesday=1)
    elif date.weekday() == 2:
        weekday_filter = Q(wednesday=1)
    elif date.weekday() == 3:
        weekday_filter = Q(thursday=1)
    elif date.weekday() == 4:
        weekday_filter = Q(friday=1)
    elif date.weekday() == 5:
        weekday_filter = Q(saturday=1)
    else:
        weekday_filter = Q(sunday=1)

    service = Calendar.objects.filter(Q(start_date__lte=date) & Q(end_date__gte=date) & weekday_filter)
    service_ids.extend(list(service.values_list('service_id', flat=True)))

    return service_ids


def get_stop_times(stop, date, num_of_stations, time_offset, current_time, all_day=False):
    service_ids = get_service_ids(date)

    future_filter = Q(departure_time_an__gt=current_time + timedelta(minutes=time_offset))

    stimes = stop.stop_times \
        .annotate(departure_time_an=ExpressionWrapper(F('departure_time') + F('delay_departure') + date, output_field=fields.DateTimeField())) \
        .annotate(arrival_time_an=ExpressionWrapper(F('arrival_time') + F('delay_arrival') + date, output_field=fields.DateTimeField())) \
        .filter(Q(trip__service_id__in=service_ids)).order_by('departure_time_an')

    return stimes.filter(future_filter)[:num_of_stations] if not all_day else stimes


def station(request):
    station_id = request.GET.get('id')
    td = int(request.GET.get('td', 0))
    ad = bool(request.GET.get('ad', 0))

    station = Stop.objects.get(stop_id=station_id)
    stops = station.stops.all() if station.stops.all() else [station]

    current_time = datetime.now()
    weekday_enum = ["Pon", "Uto", "Sri", "Čet", "Pet", "Sub", "Ned"]
    today_mid = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

    weekday = today_mid if not current_time.time().hour < 5 else today_mid - timedelta(days=1)
    days = [{'td': d, 'wd': weekday_enum[(weekday + timedelta(days=d)).weekday()], 'day': (weekday + timedelta(days=d)).day} for d in range(-1, 7)]

    day = today_mid + timedelta(days=td) if not current_time.time().hour < 5 else today_mid + timedelta(days=td - 1)

    data = {}

    for stop in stops:
        f_stimes = get_stop_times(stop, day, 25, -1, current_time, all_day=ad)
        headsigns = Trip.objects.filter(stop_times__in=f_stimes).distinct().values_list('trip_headsign', flat=True)

        data[stop.stop_id] = {'hs': ', '.join(headsigns), 'stimes': f_stimes, 'stop_code': stop.stop_code}

    return render(request, 'search/station.html', {'stops': data, 'station': station, 'days': days, 'td': td})


def save_stop(request):
    stop_id = request.GET.get('id')
    saved_stops = request.COOKIES.get('saved_stops')

    if saved_stops is None:
        saved_stops = []
    else:
        saved_stops = saved_stops.split('|')

    if stop_id in saved_stops:
        saved_stops.remove(stop_id)
        action = 0
    else:
        saved_stops.append(stop_id)
        action = 1

    response = JsonResponse({'status': 200, 'action': action})
    response.set_cookie('saved_stops', '|'.join(saved_stops), max_age=52560000)

    return response


def trip(request):
    trip_id = request.GET.get('id')
    trip = Trip.objects.get(trip_id=trip_id)

    td = int(request.GET.get('td', 0))

    current_time = datetime.now()
    today_mid = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    if current_time.time().hour < 5:
        today_mid = today_mid - timedelta(days=1)

    stops = trip.stop_times\
        .annotate(departure_time_an=ExpressionWrapper(F('departure_time') + F('delay_departure') + today_mid + timedelta(days=td), output_field=fields.DateTimeField())) \
        .annotate(arrival_time_an=ExpressionWrapper(F('arrival_time') + F('delay_arrival') + today_mid + timedelta(days=td), output_field=fields.DateTimeField())) \
        .order_by('stop_sequence')

    future_stops = stops.filter(departure_time_an__gte=current_time)

    if future_stops:
        next_stop = future_stops[0]
        past_stops = stops.filter(departure_time_an__lt=current_time)
    else:
        past_stops = stops
        next_stop = None

    return render(request, 'search/trip.html', {'trip': trip, 'past_stops': past_stops, 'future_stops': future_stops, 'next_stop': next_stop})


def route(request):
    route_id = request.GET.get('id')
    td = int(request.GET.get('td', 0))

    current_time = datetime.now()
    weekday_enum = ["Pon", "Uto", "Sri", "Čet", "Pet", "Sub", "Ned"]
    today_mid = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

    weekday = today_mid if not current_time.time().hour < 5 else today_mid - timedelta(days=1)
    days = [{'td': d, 'wd': weekday_enum[(weekday + timedelta(days=d)).weekday()], 'day': (weekday + timedelta(days=d)).day} for d in range(-1, 7)]

    day = today_mid + timedelta(days=td) if not current_time.time().hour < 5 else today_mid + timedelta(days=td - 1)

    service_ids = get_service_ids(day)

    first_stop_time = Subquery(StopTime.objects.filter(trip=OuterRef('pk')).order_by('stop_sequence').values('departure_time')[:1])
    last_stop_time = Subquery(StopTime.objects.filter(trip=OuterRef('pk')).order_by('-stop_sequence').values('arrival_time')[:1])

    first_stop = Subquery(StopTime.objects.filter(trip=OuterRef('pk')).order_by('stop_sequence').values('stop__stop_name')[:1])
    last_stop = Subquery(StopTime.objects.filter(trip=OuterRef('pk')).order_by('-stop_sequence').values('stop__stop_name')[:1])

    trips = Trip.objects.filter(route__route_id=route_id, service_id__in=service_ids) \
        .annotate(first_stop_time=ExpressionWrapper(first_stop_time + day, output_field=fields.DateTimeField())) \
        .annotate(last_stop_time=ExpressionWrapper(last_stop_time + day, output_field=fields.DateTimeField())) \
        .annotate(first_stop=first_stop).annotate(last_stop=last_stop) \
        .order_by('first_stop_time')

    route = Route.objects.get(route_id=route_id)

    return render(request, 'search/route.html', {'route': route, 'trips': trips, 'days': days, 'td': td})