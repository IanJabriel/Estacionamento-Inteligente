from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Incident
from schemas import IncidentOut

router = APIRouter(prefix="/api/v1/incidents", tags=["Incidents"])


@router.get("", response_model=List[IncidentOut])
def list_incidents(
    status: Optional[str] = Query(None),
    sectorId: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Incident)
    if status:
        q = q.filter(Incident.status == status)
    if sectorId:
        q = q.filter(Incident.sectorId == sectorId)
    rows = q.order_by(Incident.tsOpen.desc()).limit(500).all()
    return [IncidentOut.model_validate(r) for r in rows]
