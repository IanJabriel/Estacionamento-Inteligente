from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models import SpotEvent


def turnover(db: Session, sector_id: str, from_ts: datetime, to_ts: datetime) -> dict:
    """
    Count state transitions per sector and average dwell time per state.
    """
    rows = (
        db.query(SpotEvent)
        .filter(
            SpotEvent.sectorId == sector_id,
            SpotEvent.ts >= from_ts,
            SpotEvent.ts <= to_ts,
        )
        .order_by(SpotEvent.spotId, SpotEvent.ts)
        .all()
    )

    transitions = 0
    occ_durs = []
    free_durs = []

    by_spot: dict[str, list[SpotEvent]] = {}
    for r in rows:
        by_spot.setdefault(r.spotId, []).append(r)

    for spot_id, events in by_spot.items():
        prev = None
        for e in events:
            if prev is None:
                prev = e
                continue
            if e.state != prev.state:
                transitions += 1
                dur_min = (e.ts - prev.ts).total_seconds() / 60.0
                if prev.state == "OCCUPIED":
                    occ_durs.append(dur_min)
                elif prev.state == "FREE":
                    free_durs.append(dur_min)
                prev = e
            else:
                prev = e

    return {
        "sectorId": sector_id,
        "fromTs": from_ts,
        "toTs": to_ts,
        "transitions": transitions,
        "avgOccupiedDurationMin": round(sum(occ_durs) / len(occ_durs), 2) if occ_durs else None,
        "avgFreeDurationMin": round(sum(free_durs) / len(free_durs), 2) if free_durs else None,
    }
