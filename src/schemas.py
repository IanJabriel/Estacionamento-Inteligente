from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class EventPayload(BaseModel):
    eventId: str
    ts: datetime
    sectorId: str
    spotId: str
    state: str
    source: Optional[str] = "sensor"


class SpotOut(BaseModel):
    spotId: str
    sectorId: str
    currentState: str
    lastChangeTs: Optional[datetime]

    model_config = {"from_attributes": True}


class SectorOut(BaseModel):
    sectorId: str
    totalSpots: int
    occupiedCount: int
    freeCount: int
    occupancyRate: float


class MapOut(BaseModel):
    ts: datetime
    sectors: List[SectorOut]
    spots: List[SpotOut]


class IncidentOut(BaseModel):
    id: int
    tsOpen: datetime
    tsClose: Optional[datetime]
    type: str
    severity: str
    sectorId: str
    spotId: Optional[str]
    status: str
    evidenceJson: str

    model_config = {"from_attributes": True}


class RecommendationOut(BaseModel):
    fromSector: str
    recommendedSector: Optional[str]
    reason: str
    ts: datetime


class TurnoverOut(BaseModel):
    sectorId: str
    fromTs: datetime
    toTs: datetime
    transitions: int
    avgOccupiedDurationMin: Optional[float] = None
    avgFreeDurationMin: Optional[float] = None
