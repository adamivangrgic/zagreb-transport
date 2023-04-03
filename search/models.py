from django.db import models
from django.contrib.gis.db import models
from datetime import timedelta

from django.utils.functional import cached_property


class Agency(models.Model):
    agency_id = models.CharField(primary_key=True, max_length=10)
    agency_name = models.CharField(max_length=100)
    agency_url = models.URLField(max_length=200)
    agency_phone = models.CharField(max_length=20)
    agency_email = models.EmailField(max_length=20)
    agency_fare_url = models.EmailField(max_length=200)
    provider = models.CharField(max_length=10)


class Stop(models.Model):
    stop_id = models.CharField(primary_key=True, max_length=10)
    stop_name = models.CharField(max_length=200, db_index=True)
    stop_code = models.CharField(max_length=10, blank=True, null=True)
    stop_loc = models.PointField(blank=True, null=True)
    parent_station = models.ForeignKey('self', on_delete=models.CASCADE, related_name='stops', blank=True, null=True)
    location_type = models.IntegerField(blank=True, null=True)

    provider = models.CharField(max_length=10)
    stop_route_type = models.IntegerField(blank=True, null=True)
    has_trips = models.BooleanField(default=False)

    def __str__(self):
        return "{} - {}".format(self.stop_id, self.stop_name)


class Route(models.Model):
    route_id = models.CharField(primary_key=True, max_length=10)
    route_short_name = models.CharField(max_length=50, blank=True, null=True)
    route_long_name = models.CharField(max_length=200)
    route_type = models.IntegerField()
    route_color = models.CharField(max_length=6, blank=True, null=True)
    route_text_color = models.CharField(max_length=6, blank=True, null=True)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='routes', blank=True, null=True)
    provider = models.CharField(max_length=10)

    def __str__(self):
        return "{} - {}".format(self.route_short_name, self.route_long_name)


class Trip(models.Model):
    trip_id = models.CharField(primary_key=True, max_length=100)
    trip_headsign = models.CharField(max_length=200)
    trip_short_name = models.CharField(max_length=50, blank=True, null=True)
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='trips')
    service_id = models.CharField(max_length=20)
    block_id = models.IntegerField(blank=True, null=True)
    bikes_allowed = models.IntegerField(blank=True, null=True)
    wheelchair_accessible = models.IntegerField(blank=True, null=True)
    provider = models.CharField(max_length=10)

    checked_integrity_at = models.DateTimeField(null=True)

    def __str__(self):
        return "{} - {}".format(self.trip_id, self.route.route_long_name)


class StopTime(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='stop_times')
    arrival_time = models.DurationField()
    departure_time = models.DurationField()
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name='stop_times')
    stop_sequence = models.IntegerField()

    delay_arrival = models.DurationField(default=timedelta)
    delay_departure = models.DurationField(default=timedelta)
    updated_at = models.DateTimeField(null=True)
    wait_updated_at = models.DateTimeField(null=True)

    provider = models.CharField(max_length=10)

    def __str__(self):
        return "{} -- {} - {}".format(self.trip, self.departure_time, self.stop)


class Calendar(models.Model):
    service_id = models.CharField(max_length=20)
    monday = models.BooleanField()
    tuesday = models.BooleanField()
    wednesday = models.BooleanField()
    thursday = models.BooleanField()
    friday = models.BooleanField()
    saturday = models.BooleanField()
    sunday = models.BooleanField()
    start_date = models.DateField()
    end_date = models.DateField()
    provider = models.CharField(max_length=10)


class CalendarDate(models.Model):
    service_id = models.CharField(max_length=20)
    date = models.DateField()
    exception_type = models.IntegerField()
    provider = models.CharField(max_length=10)

    def __str__(self):
        return "{} - {} - {}".format(self.service_id, self.date, self.exception_type)
