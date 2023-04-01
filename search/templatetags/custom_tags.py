from django import template
from datetime import datetime, timedelta
from zet_live.settings import TIME_ZONE
import pytz

register = template.Library()


@register.filter(name='within_last')
def within_last(value, arg):
    if not value: return False
    return datetime.now().timestamp() - value.timestamp() < timedelta(minutes=arg).seconds


@register.filter(name='arrived')
def arrived(value, arg):
    if not value: return False
    return 0 < datetime.now().timestamp() - value.timestamp() < timedelta(minutes=arg).seconds


@register.filter(name='min_convert')
def min_convert(value):
    if None: return None
    sec = value.timestamp() - datetime.now().timestamp()
    # if sec < 60: return sec
    return "{} min".format(int(sec // 60)) if 0 < sec < 600 else value.strftime("%H:%M") #.astimezone(pytz.timezone(TIME_ZONE))


@register.filter(name='delay_min')
def delay_min(value):
    return int(round(value.total_seconds() / 60))


@register.filter(name='subtract')
def subtract(value, arg):
    return value - arg


@register.filter(name='signed')
def subtract(value):
    if value >= 0:
        return '+{}'.format(value)
    else:
        return '{}'.format(value)

@register.filter(name='abs')
def absolute(value):
    return abs(value)