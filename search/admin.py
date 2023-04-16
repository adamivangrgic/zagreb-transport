from django.contrib import admin

from .models import *

admin.site.register(Trip)
admin.site.register(Route)
admin.site.register(CalendarDate)
admin.site.register(Agency)
admin.site.register(Calendar)

admin.site.register(NewsEntry)

###

class StopTimeAdmin(admin.ModelAdmin):
    readonly_fields = ('trip',
                       'stop',
                       'delay_arrival',
                       'delay_departure',
                       'updated_at',
                       )
    search_fields = (
        "trip__trip_id",
        "pk",
    )


admin.site.register(StopTime, StopTimeAdmin)

###

class StopAdmin(admin.ModelAdmin):
    search_fields = (
        "stop_id",
    )


admin.site.register(Stop, StopAdmin)