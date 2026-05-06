import json
from datetime import datetime
from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Spot, SectorSnapshot
import config


def sector_stats(db: Session) -> Dict[str, dict]:
    rows = (
        db.query(Spot.sectorId, Spot.currentState, func.count(Spot.spotId))
        .group_by(Spot.sectorId, Spot.currentState)
        .all()
    )
    stats: Dict[str, dict] = {
        s: {"sectorId": s, "totalSpots": 0, "occupiedCount": 0, "freeCount": 0, "occupancyRate": 0.0}
        for s in config.SECTORS
    }
    for sector_id, state, count in rows:
        if sector_id not in stats:
            stats[sector_id] = {"sectorId": sector_id, "totalSpots": 0, "occupiedCount": 0, "freeCount": 0, "occupancyRate": 0.0}
        stats[sector_id]["totalSpots"] += count
        if state == "OCCUPIED":
            stats[sector_id]["occupiedCount"] += count
        elif state == "FREE":
            stats[sector_id]["freeCount"] += count

    for s in stats.values():
        total = s["totalSpots"]
        s["occupancyRate"] = round(s["occupiedCount"] / total, 4) if total else 0.0
    return stats


def free_spots(db: Session, sector_id: str, limit: int = 10) -> List[Spot]:
    return (
        db.query(Spot)
        .filter(Spot.sectorId == sector_id, Spot.currentState == "FREE")
        .order_by(Spot.spotId)
        .limit(limit)
        .all()
    )


def take_snapshot(db: Session) -> None:
    stats = sector_stats(db)
    now = datetime.utcnow()
    for s in stats.values():
        db.add(
            SectorSnapshot(
                ts=now,
                sectorId=s["sectorId"],
                occupiedCount=s["occupiedCount"],
                freeCount=s["freeCount"],
                occupancyRate=s["occupancyRate"],
            )
        )
    db.commit()
