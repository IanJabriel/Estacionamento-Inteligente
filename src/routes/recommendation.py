from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas import RecommendationOut
from services.recommendation import build_recommendation

router = APIRouter(prefix="/api/v1/recommendation", tags=["recommendation"])


@router.get("", response_model=RecommendationOut)
def get_recommendation(
    fromSector: str = Query(...),
    db: Session = Depends(get_db),
):
    rec = build_recommendation(db, fromSector)
    return RecommendationOut(**rec)
