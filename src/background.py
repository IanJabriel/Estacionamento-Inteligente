import logging
import threading
import time

from database import SessionLocal
from services.incidents import scan_incidents
from services.sectors import take_snapshot
import config

log = logging.getLogger("background")


class PeriodicWorker:
    def __init__(self, interval: int, fn, name: str):
        self.interval = interval
        self.fn = fn
        self.name = name
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _run(self):
        while not self._stop.is_set():
            try:
                with SessionLocal() as db:
                    self.fn(db)
            except Exception:
                log.exception("%s worker error", self.name)
            self._stop.wait(self.interval)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name=self.name, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()


incident_worker = PeriodicWorker(config.INCIDENT_SCAN_INTERVAL_SEC, scan_incidents, "incident-scan")
snapshot_worker = PeriodicWorker(config.SNAPSHOT_INTERVAL_SEC, take_snapshot, "snapshot")
