import json
import logging
import threading
import time
import paho.mqtt.client as mqtt

import config
from database import SessionLocal
from services.ingestion import ingest_event

log = logging.getLogger("mqtt")


class MqttConsumer:
    def __init__(self):
        self.client = mqtt.Client(client_id=config.MQTT_CLIENT_ID, clean_session=True)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            log.info("Connected to MQTT %s:%s", config.MQTT_HOST, config.MQTT_PORT)
            client.subscribe(config.EVENTS_TOPIC, qos=1)
            client.subscribe(config.GATEWAY_TOPIC, qos=1)
        else:
            log.error("MQTT connect failed rc=%s", rc)

    def _on_disconnect(self, client, userdata, rc):
        log.warning("MQTT disconnected rc=%s", rc)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception as e:
            log.warning("Bad payload on %s: %s", msg.topic, e)
            return

        if msg.topic.endswith("/gateway/status"):
            log.debug("gateway status %s -> %s", msg.topic, payload)
            return

        with SessionLocal() as db:
            try:
                ingest_event(db, payload)
            except Exception:
                log.exception("Ingestion failure for %s", payload)
                db.rollback()

    def _run(self):
        backoff = 1
        while not self._stop.is_set():
            try:
                self.client.connect(config.MQTT_HOST, config.MQTT_PORT, config.MQTT_KEEPALIVE)
                self.client.loop_forever(retry_first_connection=False)
            except Exception as e:
                log.warning("MQTT loop error: %s; retrying in %ss", e, backoff)
                if self._stop.wait(backoff):
                    break
                backoff = min(backoff * 2, 30)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="mqtt-consumer", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        try:
            self.client.disconnect()
        except Exception:
            pass


consumer = MqttConsumer()
