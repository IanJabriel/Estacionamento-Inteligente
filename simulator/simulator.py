"""
Comportamento:
- 90 vagas (A/B/C × 30), cada uma roda como corrotina independente
- Escala de tempo: 1 segundo real = 1 minuto simulado (TIME_FACTOR=60)
- Transições realistas: FREE → OCCUPIED em 5–30 min sim, OCCUPIED → FREE em 30–360 min sim
- Bias de horário de pico (8–10h e 17–19h): vagas ocupam mais rápido
- Falhas injetáveis via failures.json (relido a cada tick):
    stuck_occupied → trava a vaga como OCCUPIED
    stuck_free     → trava a vaga como FREE
    flapping       → surto de 5 trocas rápidas, depois limpa
"""

import asyncio
import json
import logging
import os
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s simulator :: %(message)s",
)
log = logging.getLogger("simulator")

# Configurações via env (compatíveis com docker-compose.yml existente)
MQTT_HOST    = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT    = int(os.getenv("MQTT_PORT", "1883"))
TIME_FACTOR  = int(os.getenv("TIME_FACTOR", "5"))        # 1s real = 1min simulado
FAILURES_PATH = Path(os.getenv("FAILURES_PATH", "/app/failures.json"))

SECTORS          = ["A", "B", "C"]
SPOTS_PER_SECTOR = 30

# Horários de pico em horas simuladas
PEAK_HOURS = [(8, 10), (17, 19)]


# Helpers 

def simulated_hour() -> int:
    """Retorna a hora simulada atual (0–23), baseada no tempo real escalado."""
    elapsed_real_sec = (datetime.now() - _SIM_START_REAL).total_seconds()
    elapsed_sim_min  = elapsed_real_sec * TIME_FACTOR
    return int((elapsed_sim_min / 60) % 24)


def is_peak() -> bool:
    h = simulated_hour()
    return any(start <= h < end for start, end in PEAK_HOURS)


def wait_seconds(state: str) -> float:
    """
    Converte tempo simulado (minutos) para tempo real (segundos).
    Durante horário de pico, vagas livres ocupam mais rápido.
    """
    peak = is_peak()
    if state == "FREE":
        sim_min = random.randint(5, 15) if peak else random.randint(5, 30)
    else:
        sim_min = random.randint(30, 180) if peak else random.randint(30, 360)
    return sim_min / TIME_FACTOR


def load_failures() -> dict:
    """Lê failures.json e retorna sets por tipo. Tolerante a erros."""
    if not FAILURES_PATH.exists():
        return {"stuck_occupied": set(), "stuck_free": set(), "flapping": set()}
    try:
        with FAILURES_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "stuck_occupied": set(data.get("stuck_occupied") or []),
            "stuck_free":     set(data.get("stuck_free") or []),
            "flapping":       set(data.get("flapping") or []),
        }
    except Exception as e:
        log.warning("Falha ao ler %s: %s", FAILURES_PATH, e)
        return {"stuck_occupied": set(), "stuck_free": set(), "flapping": set()}


#  Spot 

class ParkingSpot:
    def __init__(self, sector: str, number: int):
        self.sector  = sector
        self.id      = f"{sector}-{number:02d}"
        self.state   = "FREE" if random.random() > 0.4 else "OCCUPIED"

    def payload(self) -> dict:
        return {
            "eventId":  str(uuid.uuid4()),
            "ts":       datetime.now(tz=timezone.utc).isoformat(),
            "sectorId": self.sector,
            "spotId":   self.id,
            "state":    self.state,
            "source":   "sensor",
        }

    def topic(self) -> str:
        return f"campus/parking/sectors/{self.sector}/spots/{self.id}/events"

    def publish(self, client: mqtt.Client) -> None:
        client.publish(self.topic(), json.dumps(self.payload()), qos=1)
        log.debug("[%s] → %s", self.id, self.state)


# Corrotina por vaga 

async def simulate_spot(client: mqtt.Client, spot: ParkingSpot) -> None:
    """Corrotina que gerencia o ciclo de vida de uma vaga indefinidamente."""

    # Publica estado inicial
    spot.publish(client)

    while True:
        failures = load_failures()

        # Stuck occupied 
        if spot.id in failures["stuck_occupied"]:
            if spot.state != "OCCUPIED":
                spot.state = "OCCUPIED"
                spot.publish(client)
                log.info("[FAULT] %s travada como OCCUPIED", spot.id)
            await asyncio.sleep(10)
            continue

        # Stuck free 
        if spot.id in failures["stuck_free"]:
            if spot.state != "FREE":
                spot.state = "FREE"
                spot.publish(client)
                log.info("[FAULT] %s travada como FREE", spot.id)
            await asyncio.sleep(10)
            continue

        #  Flapping
        if spot.id in failures["flapping"]:
            log.info("[FAULT] %s iniciando surto de flapping", spot.id)
            for _ in range(5):
                spot.state = "OCCUPIED" if spot.state == "FREE" else "FREE"
                spot.publish(client)
                await asyncio.sleep(0.5)
            # Não limpa do JSON — o backend detectará o padrão; a limpeza
            # fica a cargo do operador editando failures.json
            await asyncio.sleep(5)
            continue

        # Transição normal 
        wait = wait_seconds(spot.state)
        await asyncio.sleep(wait)

        spot.state = "FREE" if spot.state == "OCCUPIED" else "OCCUPIED"
        spot.publish(client)
        log.info("[%s] → %s (horário: %dh, pico: %s)",
                 spot.id, spot.state, simulated_hour(), is_peak())


# Gateway heartbeat 

async def gateway_heartbeat(client: mqtt.Client) -> None:
    """Publica status online dos gateways a cada 30s reais."""
    while True:
        ts = datetime.now(tz=timezone.utc).isoformat()
        for sector in SECTORS:
            topic = f"campus/parking/sectors/{sector}/gateway/status"
            client.publish(topic, json.dumps({
                "ts":       ts,
                "sectorId": sector,
                "state":    "online",
                "source":   "gateway",
            }), qos=0)
        await asyncio.sleep(30)


# Main 
_SIM_START_REAL = datetime.now()


async def main() -> None:
    global _SIM_START_REAL
    _SIM_START_REAL = datetime.now()

    # Conecta ao broker
    client = mqtt.Client(client_id="parking-simulator", clean_session=True)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    log.info("Conectado ao broker %s:%s", MQTT_HOST, MQTT_PORT)

    # Cria as 90 vagas
    spots = [
        ParkingSpot(sector, n)
        for sector in SECTORS
        for n in range(1, SPOTS_PER_SECTOR + 1)
    ]

    log.info("🚀 Simulador iniciado com %d sensores. TIME_FACTOR=%d (1s=1min sim)",
             len(spots), TIME_FACTOR)

    # Lança todas as corrotinas + heartbeat
    tasks = [simulate_spot(client, spot) for spot in spots]
    tasks.append(gateway_heartbeat(client))

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        client.loop_stop()
        client.disconnect()
        log.info("Simulador parado.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Interrompido pelo usuário.")