import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models import Spot, SpotEvent
from schemas import EventPayload

log = logging.getLogger("ingestion")

VALID_STATES = {"FREE", "OCCUPIED"}


def ingest_event(db: Session, payload: dict) -> Optional[SpotEvent]:
    """
    Persist event idempotently and update current spot state.
    Returns the persisted SpotEvent, or None if duplicate / invalid.
    """
    try:
        evt = EventPayload(**payload)
    except Exception as e:
        log.warning("Invalid payload: %s err=%s", payload, e)
        return None

    if evt.state not in VALID_STATES:
        log.warning("Invalid state: %s", evt.state)
        return None

    if db.get(SpotEvent, evt.eventId) is not None:
        return None

    raw = json.dumps(payload, default=str)
    row = SpotEvent(
        eventId=evt.eventId,
        ts=evt.ts.replace(tzinfo=None) if evt.ts.tzinfo else evt.ts,
        sectorId=evt.sectorId,
        spotId=evt.spotId,
        state=evt.state,
        rawPayloadJson=raw,
    )
    db.add(row)

    spot = db.get(Spot, evt.spotId)
    if spot is None:
        spot = Spot(
            spotId=evt.spotId,
            sectorId=evt.sectorId,
            currentState=evt.state,
            lastChangeTs=row.ts,
            lastEventId=evt.eventId,
        )
        db.add(spot)
    else:
        if spot.currentState != evt.state:
            spot.currentState = evt.state
            spot.lastChangeTs = row.ts
        spot.lastEventId = evt.eventId

    db.commit()
    return row
