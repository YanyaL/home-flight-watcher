from django.contrib import admin

from .models import Alert, FlightOfferRecord, ScanSnapshot

admin.site.register(ScanSnapshot)
admin.site.register(FlightOfferRecord)
admin.site.register(Alert)
