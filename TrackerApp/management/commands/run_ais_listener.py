import asyncio
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand
from TrackerApp.models import Vessel
from TrackerApp.services import VesselDataService

REFRESH_SECONDS = 300  # reconnect every 5 min to pick up newly added vessels


class Command(BaseCommand):
    help = 'Runs the 24/7 asynchronous AIS WebSocket stream listener.'

    def handle(self, *args, **options):
        api_key = getattr(settings, 'AISSTREAM_API_KEY', None)
        if not api_key:
            self.stdout.write(self.style.ERROR("AISSTREAM_API_KEY is not set in Django settings!"))
            return

        self.stdout.write(self.style.SUCCESS("Starting AIS listener..."))

        @sync_to_async
        def get_targets():
            vessels = list(Vessel.objects.values_list('imo', 'mmsi'))
            imos = [str(imo) for imo, _ in vessels]
            missing = [str(imo) for imo, mmsi in vessels if not mmsi]
            return imos, missing

        async def listener_loop():
            while True:
                target_imos, missing_mmsi = await get_targets()

                if not target_imos:
                    self.stdout.write(self.style.WARNING("No vessels in database. Retrying in 10s..."))
                    await asyncio.sleep(10)
                    continue

                if missing_mmsi:
                    self.stdout.write(self.style.WARNING(
                        f"These vessels have no MMSI and can't be tracked: {missing_mmsi}"
                    ))

                self.stdout.write(f"Tracking IMOs: {target_imos}")

                try:
                    await asyncio.wait_for(
                        VesselDataService.listen_to_ais_stream(api_key, target_imos),
                        timeout=REFRESH_SECONDS,
                    )
                except asyncio.TimeoutError:
                    self.stdout.write("Refreshing vessel list...")
                    continue  # reconnect right away with a fresh list
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Stream error: {e}. Reconnecting in 5s..."))

                # Reached on errors or if the stream ended on its own:
                # always pause so we never spin in a tight loop.
                await asyncio.sleep(5)

        try:
            asyncio.run(listener_loop())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("AIS listener stopped manually."))