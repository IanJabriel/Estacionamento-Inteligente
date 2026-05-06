import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import init_db
from mqtt_consumer import consumer
from background import incident_worker, snapshot_worker
from routes import map as map_routes
from routes import sectors as sectors_routes
from routes import reports as reports_routes
from routes import incidents as incidents_routes
from routes import recommendation as recommendation_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    consumer.start()
    incident_worker.start()
    snapshot_worker.start()
    yield
    consumer.stop()
    incident_worker.stop()
    snapshot_worker.stop()


app = FastAPI(title="Smart Parking API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(map_routes.router)
app.include_router(sectors_routes.router)
app.include_router(reports_routes.router)
app.include_router(incidents_routes.router)
app.include_router(recommendation_routes.router)
