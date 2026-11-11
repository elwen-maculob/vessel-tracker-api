import json
import time
import websockets
from asgiref.sync import sync_to_async
from django.utils import timezone
from .models import Vessel

# TEMPORARY: set to False once you've finished testing
DEBUG_UNFILTERED = False


class VesselDataService:

    @staticmethod
    async def listen_to_ais_stream(api_key, target_imos):
        uri = "wss://stream.aisstream.io/v0/stream"

        @sync_to_async
        def get_mmsis():
            return [str(m) for m in Vessel.objects
                    .filter(imo__in=target_imos)
                    .exclude(mmsi__isnull=True).exclude(mmsi="")
                    .values_list('mmsi', flat=True)]

        target_mmsis = await get_mmsis()
        if not target_mmsis:
            print("No vessels with an MMSI saved, nothing to track.", flush=True)
            return

        @sync_to_async
        def save_position(mmsi, **fields):
            Vessel.objects.filter(mmsi=mmsi).update(last_updated=timezone.now(), **fields)

        payload = {
            "APIKey": api_key,
            "BoundingBoxes": [[[-90, -180], [90, 180]]],
            "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
        }
        if not DEBUG_UNFILTERED:
            payload["FiltersShipMMSI"] = target_mmsis[:50]

        async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as ws:
            await ws.send(json.dumps(payload))
            print(f"Subscribed (unfiltered={DEBUG_UNFILTERED}). Tracking MMSIs: {target_mmsis}", flush=True)

            total = 0
            matched = 0
            last_report = time.monotonic()

            async for raw in ws:
                total += 1
                message = json.loads(raw)

                if "error" in message:
                    print(f"AISStream error: {message['error']}", flush=True)
                    continue

                if time.monotonic() - last_report > 60:
                    print(f"[heartbeat] {total} messages received, {matched} matched", flush=True)
                    last_report = time.monotonic()

                msg_type = message.get("MessageType")
                mmsi = str(message.get("MetaData", {}).get("MMSI", ""))
                if mmsi not in target_mmsis:
                    continue
                matched += 1

                body = message.get("Message", {}).get(msg_type, {})

                if msg_type == "PositionReport":
                    await save_position(
                        mmsi,
                        latitude=body.get("Latitude"),
                        longitude=body.get("Longitude"),
                        speed_over_ground=body.get("Sog"),
                        course_over_ground=body.get("Cog"),
                    )
                    print(f"Updated position for MMSI {mmsi}", flush=True)

                elif msg_type == "ShipStaticData":
                    fields = {}
                    if body.get("CallSign", "").strip():
                        fields["call_sign"] = body["CallSign"].strip()
                    if body.get("Type"):
                        fields["ship_type"] = str(body["Type"])
                    ais_dest = body.get("Destination", "").replace("@", "").strip()
                    if ais_dest:
                        fields["ais_destination"] = ais_dest
                    if body.get("MaximumStaticDraught"):
                        fields["draught"] = body["MaximumStaticDraught"]
                    if fields:
                        await save_position(mmsi, **fields)
                        print(f"Updated static data for MMSI {mmsi}", flush=True)

    @staticmethod
    def get_vessel_voyage_metrics(vessel):
        if vessel.latitude is None or vessel.longitude is None:
            return {"calculated_distance_nm": 0.0, "estimated_time_of_arrival": None}

        from .utils import VesselDistanceCalculator
        calc = VesselDistanceCalculator(
            vessel, vessel.latitude, vessel.longitude,
            vessel.destination_lat, vessel.destination_lon,
        )
        return {
            "calculated_distance_nm": calc.calculate_distance(),
            "estimated_time_of_arrival": calc.calculate_eta(vessel.speed_over_ground),
        }