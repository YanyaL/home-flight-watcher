from django.contrib import admin

from .models import Alert, FlightOfferRecord, ScanJob, ScanSnapshot, ScanTask

admin.site.register(ScanSnapshot)
admin.site.register(FlightOfferRecord)
admin.site.register(Alert)
admin.site.register(ScanJob)
admin.site.register(ScanTask)
