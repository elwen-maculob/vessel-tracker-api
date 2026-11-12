# 🚢 Asynchronous Real-Time AIS Vessel Tracker

A high-performance, asynchronous Django REST application and WebSocket listener built to track global maritime vessel locations in real time using the `aisstream.io` API. Designed for fleet management, telemetry monitoring, and automated nautical metric calculations.

---

## 🌟 Key Features

* **Real-Time Telemetry & Static Data Processing:** Captures live position updates (`PositionReport`) and vessel metadata (`ShipStaticData`) via asynchronous WebSocket streaming.
* **Dynamic Database Filtering:** Monitors target vessels by IMO/MMSI dynamically queried from PostgreSQL or local SQLite via Django ORM.
* **Resilient Connection Architecture:** Features exponential backoff reconnection strategies and custom keepalive handling to maintain zero-drop connection stability.
* **Nautical Metrics Engine:** Automatically calculates distance to destination (nautical miles) and estimated time of arrival (ETA) based on real-time speed over ground (SOG) and course over ground (COG).
* **Secure REST API:** Exposes clean CRUD endpoints via Django REST Framework, protected by environment variable configurations.

---

## 🏗️ System Architecture

```text
+------------------------------+
| AISStream API                |
| (WebSocket WSS Feed)         |
+--------------+---------------+
               |
               v
+--------------+---------------+
| Async Listener Loop          |
| (websockets + asyncio)       |
+--------------+---------------+
               |
               v
+--------------+---------------+
| Django ORM & Service Layer   |
| (sync_to_async)              |
+--------------+---------------+
               |
               v
+--------------+---------------+
| Database (SQLite/Postgres)   |
+--------------+---------------+
               ^
               |
+--------------+---------------+
| Django REST API (DRF)        |
| (GET / PATCH / DELETE)       |
+------------------------------+
```

---

## 🛠️ Tech Stack

* **Backend Framework:** Python 3.x, Django 6.1+, Django REST Framework (DRF)
* **Asynchronous & WebSockets:** `asyncio`, `websockets`, `asgiref`
* **Database:** Local SQLite (default fallback) or PostgreSQL / MySQL via `dj-database-url`
* **Configuration Management:** `python-dotenv`

---

## 🚀 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/` | Retrieve a list of all tracked vessels with current metrics |
| **GET** | `/api/{imo}/` | Retrieve detailed telemetry and static data for a single vessel by IMO |
| **POST** | `/api/` | Add a new vessel to the dynamic tracking fleet |
| **PUT/PATCH** | `/api/{imo}/` | Update specific vessel properties (e.g., destination port, coordinates) |
| **DELETE** | `/api/{imo}/` | Remove a vessel from the tracking database |

### Sample Response (`GET /api/9774264/`)

```json
{
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
```

---

## ⚡ Local Setup Instructions for Evaluators & Recruiters

### 1. Clone & Setup Virtual Environment

```bash
git clone https://github.com/elwen-maculob/vessel-tracker-api.git
cd vessel-tracker-api
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```env
DEBUG=True
SECRET_KEY=local-dev-secret-key-change-me
AISSTREAM_API_KEY=your_actual_aisstream_api_key_here
```

### 3. Initialize Database & Run Migrations

```bash
python manage.py migrate
```

### 4. Run Services

* **Terminal 1 (AIS WebSocket Listener):**

```bash
python manage.py run_ais_listener
```

* **Terminal 2 (Django REST Server):**

```bash
python manage.py runserver
```