import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Spot, SpotEvent, Incident
import config

log = logging.getLogger("incidents")


def scan_incidents(db: Session) -> int:
    """
    Detect STUCK_OCCUPIED, STUCK_FREE, and FLAPPING. Returns number of incidents opened.
    """
    now = datetime.utcnow()
    opened = 0

    open_keys = {
        (i.type, i.spotId)
        for i in db.query(Incident).filter(Incident.status == "open").all()
    }

    spots = db.query(Spot).all()
    for spot in spots:
        last_change = spot.lastChangeTs or now
        idle_min = (now - last_change).total_seconds() / 60.0

        if spot.currentState == "OCCUPIED" and idle_min >= config.STUCK_OCCUPIED_MIN:
            key = ("STUCK_OCCUPIED", spot.spotId)
            if key not in open_keys:
                db.add(Incident(
                    tsOpen=now,
                    type="STUCK_OCCUPIED",
                    severity="warning",
                    sectorId=spot.sectorId,
                    spotId=spot.spotId,
                    evidenceJson=json.dumps({
                        "lastChangeTs": last_change.isoformat(),
                        "idleMinutes": round(idle_min, 1),
                        "thresholdMin": config.STUCK_OCCUPIED_MIN,
                    }),
                    status="open",
                ))
                opened += 1

        if spot.currentState == "FREE" and idle_min >= config.STUCK_FREE_MIN:
            key = ("STUCK_FREE", spot.spotId)
            if key not in open_keys:
                db.add(Incident(
                    tsOpen=now,
                    type="STUCK_FREE",
                    severity="info",
                    sectorId=spot.sectorId,
                    spotId=spot.spotId,
                    evidenceJson=json.dumps({
                        "lastChangeTs": last_change.isoformat(),
                        "idleMinutes": round(idle_min, 1),
                        "thresholdMin": config.STUCK_FREE_MIN,
                    }),
                    status="open",
                ))
                opened += 1

    window_start = now - timedelta(minutes=config.FLAPPING_WINDOW_MIN)
    flap_rows = (
        db.query(SpotEvent.spotId, SpotEvent.sectorId, func.count(SpotEvent.eventId))
        .filter(SpotEvent.ts >= window_start)
        .group_by(SpotEvent.spotId, SpotEvent.sectorId)
        .having(func.count(SpotEvent.eventId) >= config.FLAPPING_MAX_CHANGES)
        .all()
    )
    for spot_id, sector_id, cnt in flap_rows:
        key = ("FLAPPING", spot_id)
        if key not in open_keys:
            db.add(Incident(
                tsOpen=now,
                type="FLAPPING",
                severity="critical",
                sectorId=sector_id,
                spotId=spot_id,
                evidenceJson=json.dumps({
                    "windowMin": config.FLAPPING_WINDOW_MIN,
                    "events": int(cnt),
                    "thresholdEvents": config.FLAPPING_MAX_CHANGES,
                }),
                status="open",
            ))
            opened += 1

    if opened:
        db.commit()
        log.info("Opened %d incident(s)", opened)
    return opened
