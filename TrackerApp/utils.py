from . import models
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

class VesselDistanceCalculator:
    def __init__(self, vessel, vsl_lat, vsl_lon, dest_lat, dest_lon):
        self.vessel = vessel
        self.dest_lat = dest_lat
        self.dest_lon = dest_lon
        self.vsl_lat = vsl_lat
        self.vsl_lon = vsl_lon

    def calculate_distance(self):
        if None in (self.dest_lat, self.dest_lon, self.vsl_lat, self.vsl_lon):
            return 0.0

        dest_lat_rad = radians(self.dest_lat)
        dest_lon_rad = radians(self.dest_lon)
        vsl_lat_rad = radians(self.vsl_lat)
        vsl_lon_rad = radians(self.vsl_lon)

        delta_lat = vsl_lat_rad - dest_lat_rad
        delta_lon = vsl_lon_rad - dest_lon_rad

        a = sin(delta_lat / 2) ** 2 + cos(dest_lat_rad) * cos(vsl_lat_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        radius_earth_nm = 3440.065
        distance_nm = radius_earth_nm * c
        return round(distance_nm, 2)

    def calculate_time_to_destination(self, speed_over_ground):
        route_deviation_factor = 1.1
        corrected_distance = self.calculate_distance() * route_deviation_factor
        if speed_over_ground and 1.0 <= speed_over_ground < 102.3:
            return corrected_distance / speed_over_ground
        return 0.0

    def calculate_eta(self, speed_over_ground):
        time_in_hours = self.calculate_time_to_destination(speed_over_ground)
        if time_in_hours == 0.0:
            return None
        pht_zone = ZoneInfo("Asia/Manila")
        eta = datetime.now(pht_zone) + timedelta(hours=time_in_hours)
        return eta