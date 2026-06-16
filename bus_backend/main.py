"""
FastAPI entrypoint.

Run locally (from repository root):
  uvicorn bus_backend.main:app --reload

Before first run, create the database and enable PostGIS:
  CREATE DATABASE bus_app;
  \\c bus_app
  CREATE EXTENSION IF NOT EXISTS postgis;
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bus_backend.api import auth_routes, bus_routes, company_routes, timetable_routes
from bus_backend.app.database import engine
from bus_backend.app.models import Base
from bus_backend.core.seed_timetable_buses import seed_timetable_buses_if_missing


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Dev convenience: creates tables. For production, prefer Alembic migrations.
    Base.metadata.create_all(bind=engine)
    seed_timetable_buses_if_missing()
    yield


app = FastAPI(
    title="Bus Backend API",
    description="Starter API for a bus app (auth, companies, buses, routes, timetables).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(company_routes.router)
app.include_router(bus_routes.router)
app.include_router(bus_routes.routes_router)
app.include_router(timetable_routes.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
