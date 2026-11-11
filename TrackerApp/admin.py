from django.contrib import admin
from .models import Vessel

@admin.register(Vessel)
class VesselAdmin(admin.ModelAdmin):
    list_display = ("name", "imo", "mmsi", "latitude", "longitude", "speed_over_ground", "last_updated")
