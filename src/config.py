import os

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "parking-api")

DB_PATH = os.getenv("DB_PATH", "/app/data/parking.db")
DB_URL = f"sqlite:///{DB_PATH}"

SECTORS = ["A", "B", "C"]
SPOTS_PER_SECTOR = 30

OCCUPANCY_THRESHOLD = float(os.getenv("OCCUPANCY_THRESHOLD", "0.90"))

STUCK_OCCUPIED_MIN = int(os.getenv("STUCK_OCCUPIED_MIN", "240"))
STUCK_FREE_MIN = int(os.getenv("STUCK_FREE_MIN", "1440"))
FLAPPING_WINDOW_MIN = int(os.getenv("FLAPPING_WINDOW_MIN", "5"))
FLAPPING_MAX_CHANGES = int(os.getenv("FLAPPING_MAX_CHANGES", "8"))

INCIDENT_SCAN_INTERVAL_SEC = int(os.getenv("INCIDENT_SCAN_INTERVAL_SEC", "30"))
SNAPSHOT_INTERVAL_SEC = int(os.getenv("SNAPSHOT_INTERVAL_SEC", "60"))

EVENTS_TOPIC = "campus/parking/sectors/+/spots/+/events"
GATEWAY_TOPIC = "campus/parking/sectors/+/gateway/status"
