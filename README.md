🚢 Asynchronous Real-Time AIS Vessel TrackerA high-performance, asynchronous Django REST application and WebSocket listener built to track global maritime vessel locations in real time using the aisstream.io API. Designed for fleet management, telemetry monitoring, and automated nautical metric calculations.🌟 Key FeaturesReal-Time Telemetry & Static Data Processing: Captures live position updates (PositionReport) and vessel metadata (ShipStaticData) via asynchronous WebSocket streaming.Dynamic Database Filtering: Monitors target vessels by IMO/MMSI dynamically queried from PostgreSQL or local SQLite via Django ORM.Resilient Connection Architecture: Features exponential backoff reconnection strategies and custom keepalive handling to maintain zero-drop connection stability.Nautical Metrics Engine: Automatically calculates distance to destination (nautical miles) and estimated time of arrival (ETA) based on real-time speed over ground (SOG) and course over ground (COG).Secure REST API: Exposes clean CRUD endpoints via Django REST Framework, protected by environment variable configurations.🏗 System Architecture               +-----------------------+
               |    AISStream API      |
               | (WebSocket WSS Feed)  |
               +-----------+-----------+
                           |
                           v
              +------------+------------+
              | Async Listener Loop     |
              | (websockets + asyncio)  |
              +------------+------------+
                           |
                           v
              +------------+------------+
              | Django ORM & Service    |
              | Layer (sync_to_async)   |
              +------------+------------+
                           |
                           v
              +------------+------------+
              | Database (SQLite/Postgres)|
              +------------+------------+
                           ^
                           |
              +------------+------------+
              |  Django REST API (DRF)  |
              |  (GET / PATCH / DELETE) |
              +-------------------------+
🛠 Tech StackBackend Framework: Python 3.x, Django 6.1+, Django REST Framework (DRF)Asynchronous & WebSockets: asyncio, websockets, asgirefDatabase: Local SQLite (default fallback) or PostgreSQL / MySQL via dj-database-urlConfiguration Management: python-dotenv🚀 API EndpointsMethodEndpointDescriptionGET/api/Retrieve a list of all tracked vessels with current metricsGET/api/{imo}/Retrieve detailed telemetry and static data for a single vessel by IMOPOST/api/Add a new vessel to the dynamic tracking fleetPUT/PATCH/api/{imo}/Update specific vessel properties (e.g., destination port, coordinates)DELETE/api/{imo}/Remove a vessel from the tracking databaseSample Response (GET /api/9774264/){
  "id": 1,
  "name": "NAVIOS CORAL",
  "imo": "9774264",
  "mmsi": "354552000",
  "call_sign": "3FBB",
  "ship_type": "70",
  "ais_destination": "PSC PORT VILLANUEVA",
  "destination_port": "PSC PORT VILLANUEVA, PHILS",
  "destination_lat": 8.5778,
  "destination_lon": 124.7594,
  "draught": 7.6,
  "latitude": -23.90551,
  "longitude": 151.682151666667,
  "speed_over_ground": 0.1,
  "course_over_ground": 287.3,
  "navigational_status": "At anchor",
  "last_updated": "2026-11-11T07:26:35.377203Z",
  "calculated_distance_nm": 2509.2,
  "estimated_time_of_arrival": null
}
⚡ Local Setup Instructions for Evaluators & Recruiters1. Clone & Setup Virtual Environmentgit clone https://github.com/elwen-maculob/vessel-tracker.git
cd vessel-tracker
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
2. Configure Environment VariablesCreate a .env file in the root directory:SECRET_KEY=local-dev-secret-key-change-me
DEBUG=True
AISSTREAM_API_KEY=your_actual_aisstream_api_key_here
3. Initialize Database & Run Migrationspython manage.py migrate
4. Launch ServicesTerminal 1 (Django REST API Server):python manage.py runserver
Terminal 2 (Async AIS Stream Listener):python manage.py run_ais_listener
📌 Strategic Design NoteNote on Infrastructure Flexibility: This project is structured for effortless local evaluation via SQLite out-of-the-box, while fully supporting PostgreSQL production environments through dynamic environment injection via dj-database-url.