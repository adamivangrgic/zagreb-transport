from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('search_suggestions/', views.search_suggestions, name='search_suggestions'),
    path('station/', views.station, name='station'),
    path('trip/', views.trip, name='trip'),
    path('save_stop/', views.save_stop, name='save_stop'),
    path('route/', views.route, name='route'),

    path('location_search/', views.location_search, name='location_search'),
    path('map/', views.map, name='map'),
]