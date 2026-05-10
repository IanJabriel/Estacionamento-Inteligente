from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Spot
from schemas import SectorOut, SpotOut
from services.sectors import sector_stats, free_spots

router = APIRouter(prefix="/api/v1/sectors", tags=["Sectors"])


@router.get("", response_model=List[SectorOut])
def list_sectors(db: Session = Depends(get_db)):
    stats = sector_stats(db)
    return [SectorOut(**s) for s in stats.values()]


@router.get("/{sectorId}/spots", response_model=List[SpotOut])
def list_spots(sectorId: str, db: Session = Depends(get_db)):
    spots = db.query(Spot).filter(Spot.sectorId == sectorId).order_by(Spot.spotId).all()
    if not spots:
        raise HTTPException(status_code=404, detail=f"Sector {sectorId} not found")
    return [SpotOut.model_validate(s) for s in spots]


@router.get("/{sectorId}/free-spots", response_model=List[SpotOut])
def list_free_spots(
    sectorId: str,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    spots = free_spots(db, sectorId, limit)
    return [SpotOut.model_validate(s) for s in spots]
