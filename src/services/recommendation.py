import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models import RecommendationLog
import config
from services.sectors import sector_stats


def build_recommendation(db: Session, from_sector: str) -> dict:
    stats = sector_stats(db)
    src = stats.get(from_sector)

    now = datetime.utcnow()

    if src is None or src["totalSpots"] == 0:
        rec = {
            "fromSector": from_sector,
            "recommendedSector": None,
            "reason": f"Sector {from_sector} not found",
            "ts": now,
        }
        _log(db, rec, stats)
        return rec

    if src["occupancyRate"] < config.OCCUPANCY_THRESHOLD:
        rec = {
            "fromSector": from_sector,
            "recommendedSector": None,
            "reason": (
                f"Sector {from_sector} at {round(src['occupancyRate']*100)}% occupancy "
                f"(below {int(config.OCCUPANCY_THRESHOLD*100)}% threshold); no recommendation"
            ),
            "ts": now,
        }
        _log(db, rec, stats)
        return rec

    candidates = [
        s for s in stats.values()
        if s["sectorId"] != from_sector and s["freeCount"] > 0
    ]
    if not candidates:
        rec = {
            "fromSector": from_sector,
            "recommendedSector": None,
            "reason": "No alternative sector has free spots",
            "ts": now,
        }
        _log(db, rec, stats)
        return rec

    best = max(candidates, key=lambda s: s["freeCount"])
    rec = {
        "fromSector": from_sector,
        "recommendedSector": best["sectorId"],
        "reason": (
            f"Sector {from_sector} at {round(src['occupancyRate']*100)}% occupancy; "
            f"Sector {best['sectorId']} has {best['freeCount']} free spots"
        ),
        "ts": now,
    }
    _log(db, rec, stats)
    return rec


def _log(db: Session, rec: dict, stats: dict) -> None:
    db.add(
        RecommendationLog(
            ts=rec["ts"],
            fromSector=rec["fromSector"],
            recommendedSector=rec["recommendedSector"],
            reason=rec["reason"],
            dataJson=json.dumps(stats),
        )
    )
    db.commit()
