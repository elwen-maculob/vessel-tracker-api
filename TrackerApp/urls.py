from django.urls import path
from .views import VesselListCreateView, VesselDetailView

app_name = 'TrackerApp'

urlpatterns = [
    path('vessels/', VesselListCreateView.as_view(), name='vessel-list-create'),
    path('vessels/<str:imo>/', VesselDetailView.as_view(), name='vessel-detail'),
]