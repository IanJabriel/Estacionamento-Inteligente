from sqlalchemy import Column, String, Integer, Float, DateTime, Index, Text
from datetime import datetime

from database import Base


class Spot(Base):
    __tablename__ = "spots"

    spotId = Column(String, primary_key=True)
    sectorId = Column(String, index=True, nullable=False)
    currentState = Column(String, nullable=False, default="FREE")
    lastChangeTs = Column(DateTime, default=datetime.utcnow)
    lastEventId = Column(String, nullable=True)


class SpotEvent(Base):
    __tablename__ = "spot_events"

    eventId = Column(String, primary_key=True)
    ts = Column(DateTime, index=True, nullable=False)
    sectorId = Column(String, index=True, nullable=False)
    spotId = Column(String, index=True, nullable=False)
    state = Column(String, nullable=False)
    rawPayloadJson = Column(Text, nullable=False)


Index("ix_spot_events_spot_ts", SpotEvent.spotId, SpotEvent.ts)


class SectorSnapshot(Base):
    __tablename__ = "sector_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, index=True, nullable=False, default=datetime.utcnow)
    sectorId = Column(String, index=True, nullable=False)
    occupiedCount = Column(Integer, nullable=False)
    freeCount = Column(Integer, nullable=False)
    occupancyRate = Column(Float, nullable=False)


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tsOpen = Column(DateTime, nullable=False, default=datetime.utcnow)
    tsClose = Column(DateTime, nullable=True)
    type = Column(String, nullable=False)
    severity = Column(String, nullable=False, default="warning")
    sectorId = Column(String, index=True, nullable=False)
    spotId = Column(String, index=True, nullable=True)
    evidenceJson = Column(Text, nullable=False, default="{}")
    status = Column(String, index=True, nullable=False, default="open")


class RecommendationLog(Base):
    __tablename__ = "recommendations_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, index=True, nullable=False, default=datetime.utcnow)
    fromSector = Column(String, nullable=False)
    recommendedSector = Column(String, nullable=True)
    reason = Column(String, nullable=False)
    dataJson = Column(Text, nullable=False, default="{}")
