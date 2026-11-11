from rest_framework import serializers
from .models import Vessel
from .services import VesselDataService

class VesselSerializer(serializers.ModelSerializer):
    calculated_distance_nm = serializers.SerializerMethodField()
    estimated_time_of_arrival = serializers.SerializerMethodField()

    class Meta:
        model = Vessel
        fields = [
            'id',
            'name',
            'imo',
            'mmsi',
            'call_sign',
            'ship_type',
            'ais_destination',
            'destination_port',
            'destination_lat',
            'destination_lon',
            'draught',
            'latitude',
            'longitude',
            'speed_over_ground',
            'course_over_ground',
            'navigational_status',
            'last_updated',
            'calculated_distance_nm',
            'estimated_time_of_arrival',
        ]
        read_only_fields = ['id', 'last_updated', 'calculated_distance_nm', 'estimated_time_of_arrival', 'ais_destination']

    def get_calculated_distance_nm(self, obj):
        metrics = VesselDataService.get_vessel_voyage_metrics(obj)
        return metrics["calculated_distance_nm"]

    def get_estimated_time_of_arrival(self, obj):
        metrics = VesselDataService.get_vessel_voyage_metrics(obj)
        return metrics["estimated_time_of_arrival"]