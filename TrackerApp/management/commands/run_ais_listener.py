import asyncio
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand
from TrackerApp.models import Vessel
from TrackerApp.services import VesselDataService

class Command(BaseCommand):
    help = 'Runs the 24/7 asynchronous global AIS WebSocket stream listener dynamically.'

    def handle(self, *args, **options):
        api_key = getattr(settings, 'AISSTREAM_API_KEY', None)
        
        if not api_key:
            self.stdout.write(self.style.ERROR("Error: AISSTREAM_API_KEY is not set in Django settings!"))
            return

        self.stdout.write(self.style.SUCCESS("Starting dynamic global AIS listener..."))

        # Async-safe helper function to fetch IMOs from the database
        @sync_to_async
        def get_target_imos():
            imos = list(Vessel.objects.values_list('imo', flat=True))
            return [str(imo) for imo in imos]

        async def dynamic_listener_loop():
            while True:
                # 1. Fetch all target IMOs dynamically and safely from the database
                target_imos = await get_target_imos()
                
                if not target_imos:
                    self.stdout.write(self.style.WARNING("No vessels found in database to track. Retrying in 10 seconds..."))
                    await asyncio.sleep(10)
                    continue

                self.stdout.write(f"Currently tracking IMOs from DB: {target_imos}")

                try:
                    # 2. Run the stream listener with the dynamic list from the database
                    await VesselDataService.listen_to_ais_stream(api_key, target_imos)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Stream error: {e}. Reconnecting in 5 seconds..."))
                    await asyncio.sleep(5)

        try:
            asyncio.run(dynamic_listener_loop())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("AIS listener stopped manually."))