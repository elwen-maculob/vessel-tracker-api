import json
import asyncio
import websockets
from asgiref.sync import sync_to_async
from .models import Vessel

class VesselDataService:

    @staticmethod
    async def listen_to_ais_stream(api_key, target_imos):
        uri = "wss://stream.aisstream.io/v0/stream"
        
        @sync_to_async
        def get_mmsis_for_imos():
            return list(Vessel.objects.filter(imo__in=target_imos).exclude(mmsi__isnull=True).values_list('mmsi', flat=True))
        
        target_mmsis = [str(mmsi) for mmsi in await get_mmsis_for_imos()]

        # Added ping_interval and ping_timeout back to prevent idle timeout dropouts
        async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as websocket:
            subscription_payload = {
                "APIKey": api_key,
                "BoundingBoxes": [[[-90, -180], [90, 180]]], 
                "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
            }
            
            await websocket.send(json.dumps(subscription_payload))
            print(f"Subscribed to global AIS stream. Filtering locally for IMOs: {target_imos}")
            
            async for message_json in websocket:
                message = json.loads(message_json)
                msg_type = message.get("MessageType")
                
                if msg_type == "PositionReport":
                    metadata = message.get("MetaData", {})
                    imo_str = str(metadata.get("IMO", ""))
                    if not imo_str or imo_str == "0":
                        imo_str = str(message.get("Message", {}).get("PositionReport", {}).get("Imo", ""))
                    
                    if imo_str in target_imos:
                        lat = metadata.get("latitude")
                        lon = metadata.get("longitude")
                        sog = message.get("Message", {}).get("PositionReport", {}).get("Sog", 0.0)
                        cog = message.get("Message", {}).get("PositionReport", {}).get("Cog", 0.0)
                        
                        @sync_to_async
                        def update_vessel_telemetry():
                            Vessel.objects.filter(imo=imo_str).update(
                                latitude=lat,
                                longitude=lon,
                                speed_over_ground=sog,
                                course_over_ground=cog
                            )
                        
                        await update_vessel_telemetry()
                        print(f"Updated telemetry for IMO {imo_str}: Lat {lat}, Lon {lon}")

                elif msg_type == "ShipStaticData":
                    metadata = message.get("MetaData", {})
                    imo_str = str(metadata.get("IMO", ""))
                    if not imo_str or imo_str == "0":
                        imo_str = str(message.get("Message", {}).get("ShipStaticData", {}).get("Imo", ""))
                    
                    if imo_str in target_imos:
                        static_data = message.get("Message", {}).get("ShipStaticData", {})
                        call_sign = static_data.get("CallSign", "").strip()
                        ship_type = static_data.get("Type", 0)
                        
                        @sync_to_async
                        def update_vessel_static():
                            update_kwargs = {}
                            if call_sign:
                                update_kwargs['call_sign'] = call_sign
                            if ship_type:
                                update_kwargs['ship_type'] = str(ship_type)
                                
                            if update_kwargs:
                                Vessel.objects.filter(imo=imo_str).update(**update_kwargs)
                        
                        await update_vessel_static()
                        print(f"Updated static data for IMO {imo_str}")

    @staticmethod
    def get_vessel_voyage_metrics(vessel):
        if vessel.latitude is None or vessel.longitude is None:
            return {"calculated_distance_nm": 0.0, "estimated_time_of_arrival": None}
        
        from .utils import calculate_distance_and_eta
        return calculate_distance_and_eta(
            vessel.latitude, 
            vessel.longitude, 
            vessel.destination_lat, 
            vessel.destination_lon, 
            vessel.speed_over_ground
        )