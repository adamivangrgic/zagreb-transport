from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('', include('search.urls'), name='index'),
    path('admin_utils/', include('admin_utils.urls')),
    path('admin/', admin.site.urls),
    path('', include('pwa.urls')),
]