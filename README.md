# Smart Parking — MVP

Full Python MVP: FastAPI backend + Mosquitto MQTT broker + Python simulator + SQLite.
3 sectors (A, B, C) × 30 spots each = 90 spots.

> 📖 **Documentação técnica completa em [DOCUMENTACAO.md](DOCUMENTACAO.md)** — explica arquitetura, fluxo de eventos, cada tabela, cada serviço e decisões de design.

## Project layout

```
.
├── docker-compose.yml          # mosquitto + parking-api + simulator
├── mosquitto/config/           # broker config (anonymous on :1883)
├── src/                        # FastAPI backend
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # app entry, lifespan, routers
│   ├── config.py               # env-driven settings
│   ├── database.py             # SQLAlchemy engine + init/seed
│   ├── models.py               # ORM tables
│   ├── schemas.py              # Pydantic DTOs
│   ├── mqtt_consumer.py        # paho-mqtt subscriber (background thread)
│   ├── background.py           # periodic incident scan + sector snapshots
│   ├── routes/                 # REST endpoints
│   │   ├── map.py
│   │   ├── sectors.py
│   │   ├── reports.py
│   │   ├── incidents.py
│   │   └── recommendation.py
│   └── services/               # business logic
│       ├── ingestion.py        # idempotent event ingest
│       ├── sectors.py          # stats / free spots / snapshots
│       ├── recommendation.py   # rerouting logic
│       ├── incidents.py        # STUCK / FLAPPING detector
│       └── reports.py          # turnover analytics
└── simulator/                  # MQTT publisher
    ├── Dockerfile
    ├── requirements.txt
    ├── simulator.py
    └── failures.json           # injectable failures (hot-reloaded)
```

## How to run

### 1) Bring everything up with Docker

```bash
docker compose up --build
```

This starts:
- `mosquitto` on `localhost:1883`
- `parking-api` on `http://localhost:8000` (Swagger at `/docs`)
- `parking-simulator` publishing events for all 90 spots

### 2) Run components manually (without Docker)

Start the broker locally (or use Docker just for it: `docker compose up mosquitto`).

API:
```bash
cd src
pip install -r requirements.txt
set MQTT_HOST=localhost           # PowerShell: $env:MQTT_HOST="localhost"
set DB_PATH=./data/parking.db
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Simulator:
```bash
cd simulator
pip install -r requirements.txt
set MQTT_HOST=localhost
python simulator.py
```

### 3) Inject failures

Edit `simulator/failures.json` while the simulator runs (it re-reads every tick):

```json
{
  "stuck_occupied": ["A-01"],
  "stuck_free": ["B-15"],
  "flapping": ["C-07"]
}
```

`STUCK_OCCUPIED` / `STUCK_FREE` open after the spot has not changed for the configured threshold (env vars `STUCK_OCCUPIED_MIN`, `STUCK_FREE_MIN`). `FLAPPING` opens when a spot exceeds `FLAPPING_MAX_CHANGES` events within `FLAPPING_WINDOW_MIN` minutes.

## REST endpoints

| Method | Path                                                    | Purpose |
|--------|---------------------------------------------------------|---------|
| GET    | `/api/v1/map`                                           | Full map (sectors + spots + current state) |
| GET    | `/api/v1/sectors`                                       | Per-sector occupancy stats |
| GET    | `/api/v1/sectors/{sectorId}/spots`                      | All spots in sector |
| GET    | `/api/v1/sectors/{sectorId}/free-spots?limit=10`        | First N free spots |
| GET    | `/api/v1/reports/turnover?sectorId=A&from=...&to=...`   | Transitions + avg dwell |
| GET    | `/api/v1/incidents?status=open`                         | Incident list |
| GET    | `/api/v1/recommendation?fromSector=A`                   | Reroute suggestion |
| GET    | `/health`                                               | Liveness |

## MQTT topics

- Events: `campus/parking/sectors/{sectorId}/spots/{spotId}/events`
- Gateway: `campus/parking/sectors/{sectorId}/gateway/status`

Payload:
```json
{
  "eventId": "uuid",
  "ts": "2026-05-05T12:34:56Z",
  "sectorId": "A",
  "spotId": "A-01",
  "state": "OCCUPIED",
  "source": "sensor"
}
```

## Quick test

```bash
curl http://localhost:8000/api/v1/sectors
curl "http://localhost:8000/api/v1/sectors/A/free-spots?limit=5"
curl "http://localhost:8000/api/v1/recommendation?fromSector=A"
curl "http://localhost:8000/api/v1/incidents?status=open"
```

## Short explanation (≈140 words)

The backend is a FastAPI app with clean separation: `routes/` are thin HTTP adapters, `services/` hold the business logic, `models.py` is the SQLAlchemy schema, and SQLite is created/seeded automatically on startup with all 90 spots. A paho-mqtt consumer runs in a background thread, subscribes to the wildcard event topic, and persists each message through `services/ingestion.py`, which keys on `eventId` for idempotency, appends to `spot_events`, and updates the `spots` row. Two periodic workers run alongside: one takes per-sector snapshots, the other scans for STUCK and FLAPPING incidents using simple thresholds. The recommendation service triggers when occupancy ≥ 90 % and picks the sector with the most free spots. The simulator is a standalone Python script publishing realistic FREE/OCCUPIED cycles with peak-hour bias and supports hot-reloaded failure injection via `failures.json`.
