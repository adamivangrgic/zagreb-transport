from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('station/', views.station, name='station'),
    path('trip/', views.trip, name='trip'),
    path('route/', views.route, name='route'),

    path('save_stop/', views.save_stop, name='save_stop'),
    path('search_suggestions/', views.search_suggestions, name='search_suggestions'),
    path('location_search/', views.location_search, name='location_search'),
]