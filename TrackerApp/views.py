from rest_framework import generics
from .models import Vessel
from .serializers import VesselSerializer

class VesselListCreateView(generics.ListCreateAPIView):
    queryset = Vessel.objects.all().order_by('-last_updated')
    serializer_class = VesselSerializer


class VesselDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Vessel.objects.all()
    serializer_class = VesselSerializer
    lookup_field = 'imo'  # Can be changed to 'imo' if you prefer looking up by IMO number in the URL