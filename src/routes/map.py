from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Spot
from schemas import MapOut, SectorOut, SpotOut
from services.sectors import sector_stats

router = APIRouter(prefix="/api/v1", tags=["map"])


@router.get("/map", response_model=MapOut)
def get_map(db: Session = Depends(get_db)):
    stats = sector_stats(db)
    spots = db.query(Spot).order_by(Spot.spotId).all()
    return MapOut(
        ts=datetime.utcnow(),
        sectors=[SectorOut(**s) for s in stats.values()],
        spots=[SpotOut.model_validate(s) for s in spots],
    )
