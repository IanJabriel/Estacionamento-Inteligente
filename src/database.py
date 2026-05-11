import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

import config

os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)

engine = create_engine(
    config.DB_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    poolclass=StaticPool,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import Spot
    import config as cfg

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing = {s.spotId for s in db.query(Spot).all()}
        new_rows = []
        for sector in cfg.SECTORS:
            for n in range(1, cfg.SPOTS_PER_SECTOR + 1):
                spot_id = f"{sector}-{n:02d}"
                if spot_id not in existing:
                    new_rows.append(Spot(spotId=spot_id, sectorId=sector, currentState="FREE"))
        if new_rows:
            db.add_all(new_rows)
            db.commit()
