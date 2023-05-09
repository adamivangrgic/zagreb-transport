from django.shortcuts import render
from .models import *
from django.http import JsonResponse
from datetime import datetime
from django.db.models import Q, F, ExpressionWrapper, fields, Subquery, OuterRef, Case, When, IntegerField
from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.db.models.functions import Distance
from itertools import groupby


up_to_date_threshold = timedelta(minutes=90)


def calculate_median(input_list):
    n = len(input_list)
    if n == 0:
        return 0
    sorted_list = sorted(input_list)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_list[mid-1] + sorted_list[mid]) / 2
    else:
        return sorted_list[mid]

def cal_median_delay(input_list):
    res = calculate_median(input_list)
    return res if res < 20 * 60 else 0


def index(request):
    return render(request, 'search/map.html', {'id': 'index'})


def search_suggestions(request):
    query = request.GET.get('q')

    output = [[], [], [], []]  # rail 0, tram 1, bus 2, routes 3

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


    routes = Route.objects.filter(Q(route_short_name__icontains=query) | Q(route_long_name__icontains=query))[:10]
    for route in routes:
        output[3].append([route.route_short_name, route.route_long_name, route.route_id])

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
        stops = stops.exclude(has_trips=False).order_by(order_priority)[:150]
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

    stimes = stop.stop_times.filter(trip__service_id__in=service_ids) \
        .annotate(up_to_date=Case(When(updated_at__gte=current_time - up_to_date_threshold, then=True), default=False, output_field=fields.BooleanField())) \
        .annotate(departure_time_an=ExpressionWrapper(F('departure_time') + date, output_field=fields.DateTimeField()))
        
    # ### delay estimates
    # past_stimes = stimes.exclude(future_filter).filter(departure_time_an__gt=current_time - timedelta(hours=2))
    # past_delays = past_stimes.values('delay_departure', 'trip__route__route_id')

    # median_delays = {}

    # for delay in past_delays:
    #     if not delay['trip__route__route_id'] in median_delays.keys():
    #         median_delays[delay['trip__route__route_id']] = []
    #     median_delays[delay['trip__route__route_id']].append(delay['delay_departure'].total_seconds())

    # # raise Exception(median_delays)

    # stimes = stimes.annotate(median_delay=Case(
    #     *[When(trip__route__route_id=t, then=timedelta(seconds=cal_median_delay(median_delays.get(t, [])))) for t in median_delays],
    #     output_field=fields.DurationField()))

    delay_cases = Case(
        When(updated_at__gte=current_time - timedelta(minutes=4), delay_departure__gte=timedelta(minutes=30), then=F('delay_departure')), ## for likely wrong trips (extreme delay)
        When(up_to_date=True, delay_departure__lt=timedelta(minutes=30), then=F('delay_departure')), 
        # When(departure_time_an__gt=current_time, departure_time_an__lt=current_time + timedelta(hours=1), trip__route__route_id__in=median_delays.keys(), then=F('median_delay')), 
        default=timedelta(), output_field=fields.DurationField())

    stimes = stimes.annotate(delay_departure_an=delay_cases) \
        .annotate(departure_time_an=ExpressionWrapper(F('departure_time_an') + F('delay_departure_an'), output_field=fields.DateTimeField())) \
        .order_by('departure_time_an')

    return stimes.filter(future_filter)[:num_of_stations] if not all_day else stimes


def station(request):
    station_id = request.GET.get('id')
    td = int(request.GET.get('td', 0)) # time delay (usually days)
    ad = bool(request.GET.get('ad', 0)) # all day
    num = int(request.GET.get('num', 25)) # number of stations

    station = Stop.objects.get(stop_id=station_id)

    if ad:
        current_time = datetime.now()
        weekday_enum = ["Pon", "Uto", "Sri", "Čet", "Pet", "Sub", "Ned"]
        today_mid = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

        weekday = today_mid if not current_time.time().hour < 5 else today_mid - timedelta(days=1)
        days = [{'td': d, 'wd': weekday_enum[(weekday + timedelta(days=d)).weekday()], 'day': (weekday + timedelta(days=d)).day} for d in range(-1, 7)]

        return render(request, 'search/station.html', {'id': station_id, 'station': station, 'days': days, 'td': td})
        
    else:
        return render(request, 'search/map.html', {'id': station_id, 'station': station, 'num': num })


def timetable(request):
    station_id = request.GET.get('id')
    td = int(request.GET.get('td', 0)) # time delay (days)
    ad = bool(request.GET.get('ad', 0)) # all day
    num = int(request.GET.get('num', 25)) # number of stations
    to = float(request.GET.get('to', -1)) # time offset (first station cutoff in minutes from now)

    station = None
    stops = None

    if station_id == 'index':
        saved_stops = request.COOKIES.get('saved_stops')

        if not saved_stops:
            stop_ids = []
        else:
            stop_ids = saved_stops.split('|')

        data = {}
        stops = Stop.objects.filter(stop_id__in=stop_ids).order_by(Case(*[When(stop_id=id_val, then=pos) for pos, id_val in enumerate(stop_ids)]))

    else:
        station = Stop.objects.get(stop_id=station_id)
        stops = station.stops.all() if station.stops.all() else [station]

    current_time = datetime.now()
    today_mid = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

    day = today_mid + timedelta(days=td) if not current_time.time().hour < 5 else today_mid + timedelta(days=td - 1)

    data = {}

    for stop in stops:
        f_stimes = get_stop_times(stop, day, num, to, current_time, all_day=ad)
        headsigns = Trip.objects.filter(stop_times__in=f_stimes).distinct().values_list('trip_headsign', flat=True)

        data[stop.stop_id] = {'hs': ', '.join(headsigns), 'stimes': f_stimes, 'stop_code': stop.stop_code,
                              'station_name': stop.stop_name, 'provider': stop.provider, 'stop_loc': [stop.stop_loc.x, stop.stop_loc.y]}

    return render(request, 'search/timetable.html', {'station': station, 'stops': data, 'td': td, 'num': num})


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


def save_stime(request):
    stime_id = request.GET.get('id')
    saved_stimes = request.COOKIES.get('saved_stimes')

    if saved_stimes is None:
        saved_stimes = []
    else:
        saved_stimes = saved_stimes.split('|')

    if stime_id in saved_stimes:
        saved_stimes.remove(stime_id)
        action = 0
    else:
        saved_stimes.append(stime_id)
        action = 1

    response = JsonResponse({'status': 200, 'action': action})
    response.set_cookie('saved_stops', '|'.join(saved_stimes), max_age=52560000)

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
        .annotate(up_to_date=Case(When(updated_at__gte=current_time - up_to_date_threshold, then=True), default=False, output_field=fields.BooleanField())) \
        .annotate(delay_departure_an=Case(When(up_to_date=True, then=F('delay_departure')), default=timedelta(), output_field=fields.DurationField())) \
        .annotate(delay_arrival_an=Case(When(up_to_date=True, then=F('delay_arrival')), default=timedelta(), output_field=fields.DurationField())) \
        .annotate(departure_time_an=ExpressionWrapper(F('departure_time') + F('delay_departure_an') + today_mid + timedelta(days=td), output_field=fields.DateTimeField())) \
        .annotate(arrival_time_an=ExpressionWrapper(F('arrival_time') + F('delay_arrival_an') + today_mid + timedelta(days=td), output_field=fields.DateTimeField())) \
        .order_by('stop_sequence')

    future_stops = stops.filter(departure_time_an__gte=current_time)

    if future_stops:
        next_stop = future_stops[0]
        past_stops = stops.filter(departure_time_an__lt=current_time)
    else:
        past_stops = stops
        next_stop = None

    first_stop = stops[0]
    last_stop = stops[len(stops)-1]

    return render(request, 'search/trip.html', {'trip': trip, 'past_stops': past_stops, 'future_stops': future_stops,
        'next_stop': next_stop, 'first_stop': first_stop, 'last_stop': last_stop, 'td': td})


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