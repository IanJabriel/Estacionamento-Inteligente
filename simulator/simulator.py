"""
Smart Parking MQTT simulator.

- Simulates 90 spots (A/B/C * 30).
- Time scaling: 1 real second = 1 simulated minute.
- Realistic dwell times (FREE/OCCUPIED) of 30 min – 6 h.
- Peak hours bias toward OCCUPIED (8:00–10:00 and 17:00–19:00 sim time).
- Failures injectable via failures.json (re-read every loop tick):
    {
      "stuck_occupied": ["A-01"],
      "stuck_free": ["B-15"],
      "flapping": ["C-07"]
    }
"""

import json
import logging
import os
import random
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s simulator :: %(message)s",
)
log = logging.getLogger("simulator")

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
SIM_TICK_SEC = float(os.getenv("SIM_TICK_SEC", "1.0"))      # real seconds per tick
SIM_MIN_PER_TICK = float(os.getenv("SIM_MIN_PER_TICK", "1.0"))  # sim minutes per tick
FAILURES_PATH = Path(os.getenv("FAILURES_PATH", "/app/failures.json"))

SECTORS = ["A", "B", "C"]
SPOTS_PER_SECTOR = 30

PEAK_HOURS = {(8, 10), (17, 19)}  # simulated hour ranges (start inclusive, end exclusive)


@dataclass
class SpotState:
    spot_id: str
    sector_id: str
    state: str            # "FREE" | "OCCUPIED"
    next_change_sim_min: int
    flap_phase: int = 0


def topic_for(sector_id: str, spot_id: str) -> str:
    return f"campus/parking/sectors/{sector_id}/spots/{spot_id}/events"


def is_peak(sim_dt: datetime) -> bool:
    h = sim_dt.hour
    return any(start <= h < end for start, end in PEAK_HOURS)


def random_duration_min(state: str, peak: bool) -> int:
    """Return duration before next state change, biased by peak hours."""
    if state == "FREE":
        # During peak, free spots fill faster
        low, high = (15, 90) if peak else (60, 240)
    else:
        low, high = (60, 240) if peak else (45, 360)
    return random.randint(low, high)


def init_spots() -> list[SpotState]:
    spots: list[SpotState] = []
    for sector in SECTORS:
        for n in range(1, SPOTS_PER_SECTOR + 1):
            spot_id = f"{sector}-{n:02d}"
            initial = "OCCUPIED" if random.random() < 0.4 else "FREE"
            spots.append(SpotState(
                spot_id=spot_id,
                sector_id=sector,
                state=initial,
                next_change_sim_min=random_duration_min(initial, peak=False),
            ))
    return spots


def load_failures() -> dict:
    if not FAILURES_PATH.exists():
        return {}
    try:
        with FAILURES_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "stuck_occupied": set(data.get("stuck_occupied", []) or []),
            "stuck_free": set(data.get("stuck_free", []) or []),
            "flapping": set(data.get("flapping", []) or []),
        }
    except Exception as e:
        log.warning("Failed to read %s: %s", FAILURES_PATH, e)
        return {}


def publish_event(client: mqtt.Client, spot: SpotState, sim_dt: datetime) -> None:
    payload = {
        "eventId": str(uuid.uuid4()),
        "ts": sim_dt.replace(tzinfo=timezone.utc).isoformat(),
        "sectorId": spot.sector_id,
        "spotId": spot.spot_id,
        "state": spot.state,
        "source": "sensor",
    }
    client.publish(topic_for(spot.sector_id, spot.spot_id), json.dumps(payload), qos=1)


def publish_gateway_status(client: mqtt.Client, sim_dt: datetime) -> None:
    for sector in SECTORS:
        topic = f"campus/parking/sectors/{sector}/gateway/status"
        client.publish(topic, json.dumps({
            "ts": sim_dt.replace(tzinfo=timezone.utc).isoformat(),
            "sectorId": sector,
            "state": "online",
            "source": "gateway",
        }), qos=0)


def step(spots: list[SpotState], failures: dict, client: mqtt.Client, sim_dt: datetime) -> None:
    peak = is_peak(sim_dt)
    for spot in spots:
        if spot.spot_id in failures.get("stuck_occupied", set()):
            if spot.state != "OCCUPIED":
                spot.state = "OCCUPIED"
                publish_event(client, spot, sim_dt)
            spot.next_change_sim_min = 10_000  # never naturally
            continue

        if spot.spot_id in failures.get("stuck_free", set()):
            if spot.state != "FREE":
                spot.state = "FREE"
                publish_event(client, spot, sim_dt)
            spot.next_change_sim_min = 10_000
            continue

        if spot.spot_id in failures.get("flapping", set()):
            spot.state = "FREE" if spot.state == "OCCUPIED" else "OCCUPIED"
            publish_event(client, spot, sim_dt)
            continue

        spot.next_change_sim_min -= int(SIM_MIN_PER_TICK)
        if spot.next_change_sim_min <= 0:
            spot.state = "FREE" if spot.state == "OCCUPIED" else "OCCUPIED"
            spot.next_change_sim_min = random_duration_min(spot.state, peak)
            publish_event(client, spot, sim_dt)


def main() -> None:
    random.seed()
    spots = init_spots()

    client = mqtt.Client(client_id="parking-simulator", clean_session=True)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    log.info("Connected to MQTT %s:%s. Publishing initial states...", MQTT_HOST, MQTT_PORT)

    sim_dt = datetime.utcnow().replace(hour=7, minute=0, second=0, microsecond=0)

    for spot in spots:
        publish_event(client, spot, sim_dt)

    gateway_counter = 0
    try:
        while True:
            failures = load_failures()
            step(spots, failures, client, sim_dt)
            sim_dt += timedelta(minutes=int(SIM_MIN_PER_TICK))
            gateway_counter += 1
            if gateway_counter % 30 == 0:
                publish_gateway_status(client, sim_dt)
            time.sleep(SIM_TICK_SEC)
    except KeyboardInterrupt:
        log.info("Shutting down simulator")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
