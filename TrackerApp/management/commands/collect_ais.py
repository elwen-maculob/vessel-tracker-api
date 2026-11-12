"""
Short-burst AIS collector.

Connects to AISStream, listens until every tracked vessel has reported (or the
time limit is reached), saves the latest data in one batch, then exits.
Meant to be run on a schedule (for example by GitHub Actions) instead of
keeping a worker online 24/7.

Place this file at: TrackerApp/management/commands/collect_ais.py

Usage:
    python manage.py collect_ais                      # positions only, up to 300 s
    python manage.py collect_ais --statics --max-seconds 420
"""
import asyncio
import json
import time

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.utils import timezone

from TrackerApp.models import Vessel

URI = "wss://stream.aisstream.io/v0/stream"
MAX_MMSI_FILTER = 50  # AISStream accepts at most 50 MMSIs per subscription

NAV_STATUS = {
    0: "Under way using engine",
    1: "At anchor",
    2: "Not under command",
    3: "Restricted manoeuvrability",
    4: "Constrained by draught",
    5: "Moored",
    6: "Aground",
    7: "Engaged in fishing",
    8: "Under way sailing",
    11: "Towing astern",
    12: "Pushing ahead / towing alongside",
    14: "AIS-SART active",
    15: "Not defined",
}


def clean_position(body):
    """Convert an AIS PositionReport into model fields, skipping 'not available' values."""
    fields = {}

    lat, lon = body.get("Latitude"), body.get("Longitude")
    if lat is not None and lon is not None and abs(lat) <= 90 and abs(lon) <= 180:
        fields["latitude"] = lat
        fields["longitude"] = lon

    sog = body.get("Sog")
    if sog is not None and sog < 102.3:  # 102.3 = speed not available
        fields["speed_over_ground"] = sog

    cog = body.get("Cog")
    if cog is not None and cog < 360:  # 360 = course not available
        fields["course_over_ground"] = cog

    nav = body.get("NavigationalStatus")
    if nav in NAV_STATUS:
        fields["navigational_status"] = NAV_STATUS[nav]

    return fields


def clean_static(body):
    """Convert AIS ShipStaticData into model fields."""
    fields = {}

    call_sign = (body.get("CallSign") or "").replace("@", "").strip()
    if call_sign:
        fields["call_sign"] = call_sign

    if body.get("Type"):
        fields["ship_type"] = str(body["Type"])

    # The crew's typed-in destination goes to ais_destination only,
    # so destination_port (your fixed port) is never overwritten.
    destination = (body.get("Destination") or "").replace("@", "").strip()
    if destination:
        fields["ais_destination"] = destination

    if body.get("MaximumStaticDraught"):
        fields["draught"] = body["MaximumStaticDraught"]

    return fields


async def collect(api_key, mmsis, max_seconds, want_static):
    """Listen until all tracked vessels have reported, or the time limit is hit."""
    targets = set(mmsis)
    positions, statics = {}, {}
    deadline = time.monotonic() + max_seconds

    payload = {
        "APIKey": api_key,
        "BoundingBoxes": [[[-90, -180], [90, 180]]],
        "FiltersShipMMSI": list(mmsis),
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
    }

    async with websockets.connect(URI, ping_interval=20, ping_timeout=20) as ws:
        await ws.send(json.dumps(payload))

        while time.monotonic() < deadline:
            try:
                raw = await asyncio.wait_for(
                    ws.recv(), timeout=max(0.1, min(30, deadline - time.monotonic()))
                )
            except asyncio.TimeoutError:
                continue
            except ConnectionClosed:
                break

            message = json.loads(raw)

            if "error" in message:
                raise CommandError(f"AISStream returned an error: {message['error']}")

            msg_type = message.get("MessageType")
            mmsi = str(message.get("MetaData", {}).get("MMSI", ""))
            if mmsi not in targets:
                continue

            body = message.get("Message", {}).get(msg_type, {})

            if msg_type == "PositionReport":
                positions[mmsi] = clean_position(body)  # later reports replace earlier ones
            elif msg_type == "ShipStaticData":
                statics[mmsi] = clean_static(body)

            all_positions = targets <= set(positions)
            all_statics = targets <= set(statics)
            if all_positions and (not want_static or all_statics):
                break

    return positions, statics


class Command(BaseCommand):
    help = "Listens to AISStream for a short window, saves the latest data for tracked vessels, then exits."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-seconds",
            type=int,
            default=300,
            help="Stop listening after this many seconds (default: 300).",
        )
        parser.add_argument(
            "--statics",
            action="store_true",
            help="Also wait for ship static data (destination, call sign, type, draught).",
        )

    def handle(self, *args, **options):
        api_key = getattr(settings, "AISSTREAM_API_KEY", None)
        if not api_key:
            raise CommandError("AISSTREAM_API_KEY is not set.")

        mmsis = [
            str(m)
            for m in Vessel.objects.exclude(mmsi__isnull=True)
            .exclude(mmsi="")
            .values_list("mmsi", flat=True)
        ]
        if not mmsis:
            self.stdout.write("No vessels with an MMSI to track.")
            return

        if len(mmsis) > MAX_MMSI_FILTER:
            self.stdout.write(
                self.style.WARNING(
                    f"{len(mmsis)} vessels found; only the first {MAX_MMSI_FILTER} can be tracked."
                )
            )
            mmsis = mmsis[:MAX_MMSI_FILTER]

        # Release the database connection while waiting, so a serverless
        # database (like Neon) is not kept awake for the whole listening window.
        connections.close_all()

        try:
            positions, statics = asyncio.run(
                collect(api_key, mmsis, options["max_seconds"], options["statics"])
            )
        except (OSError, WebSocketException) as exc:
            raise CommandError(f"Could not reach AISStream: {exc}")

        now = timezone.now()
        saved = 0
        for mmsi in set(positions) | set(statics):
            fields = {**statics.get(mmsi, {}), **positions.get(mmsi, {})}
            # update() does not touch auto_now fields, so set last_updated explicitly
            Vessel.objects.filter(mmsi=mmsi).update(last_updated=now, **fields)
            saved += 1

        # Keep the output free of vessel names, MMSIs and positions:
        # logs of a public repository's GitHub Actions runs are visible to everyone.
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(positions)} of {len(mmsis)} vessels reported a position; "
                f"{len(statics)} sent static data; {saved} records saved."
            )
        )
