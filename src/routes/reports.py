from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas import TurnoverOut
from services.reports import turnover

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.get("/turnover", response_model=TurnoverOut)
def get_turnover(
    sectorId: str = Query(...),
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    to_ts = to or datetime.utcnow()
    from_ts = from_ or (to_ts - timedelta(hours=24))
    return TurnoverOut(**turnover(db, sectorId, from_ts, to_ts))
