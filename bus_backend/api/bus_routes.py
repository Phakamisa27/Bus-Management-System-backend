"""
Buses and routes (lines).

This file defines two routers:
- `/buses` — vehicles
- `/routes` — route/line definitions (needed for buses and timetables)
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud import buses as buses_crud
from app.crud import companies as companies_crud
from app.crud import routes as routes_crud
from app.schemas import (
    BusCreate,
    BusLocationCreate,
    BusLocationRead,
    BusRead,
    BusUpdate,
    RouteCreate,
    RouteRead,
)
from app.database import get_db
from app.models import Bus, BusLocation, Route, User
from core.auth import get_current_user

router = APIRouter(prefix="/buses", tags=["buses"])
routes_router = APIRouter(prefix="/routes", tags=["routes"])


def _company_owned(db: Session, company_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    c = companies_crud.get(db, company_id)
    return c is not None and c.owner_id == user_id


# --- /routes ---


@routes_router.get("", response_model=list[RouteRead])
def list_routes(
    db: Annotated[Session, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[Route]:
    return routes_crud.list_routes(db, skip=skip, limit=limit)


@routes_router.post("", response_model=RouteRead, status_code=status.HTTP_201_CREATED)
def create_route(
    data: RouteCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Creating a route requires login (you can relax this if you want public data)."""
    _ = current_user
    return routes_crud.create(db, data)


@routes_router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(
    route_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    row = routes_crud.get(db, route_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    _ = current_user
    routes_crud.delete(db, row)


# --- /buses ---


@router.get("", response_model=list[BusRead])
def list_buses(
    db: Annotated[Session, Depends(get_db)],
    company_id: Annotated[uuid.UUID | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[Bus]:
    if company_id is not None:
        return buses_crud.list_for_company(db, company_id)
    return buses_crud.list_all(db, skip=skip, limit=limit)


@router.post("", response_model=BusRead, status_code=status.HTTP_201_CREATED)
def create_bus(
    data: BusCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if not _company_owned(db, data.company_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company not found or not yours")
    return buses_crud.create(db, data)


@router.get("/{bus_id}", response_model=BusRead)
def get_bus(
    bus_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    row = buses_crud.get(db, bus_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    if not _company_owned(db, row.company_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return row


@router.patch("/{bus_id}", response_model=BusRead)
def update_bus(
    bus_id: uuid.UUID,
    data: BusUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    row = buses_crud.get(db, bus_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    if not _company_owned(db, row.company_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return buses_crud.update(db, row, data)


@router.delete("/{bus_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bus(
    bus_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    row = buses_crud.get(db, bus_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    if not _company_owned(db, row.company_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    buses_crud.delete(db, row)


@router.post(
    "/{bus_id}/location",
    response_model=BusLocationRead,
    status_code=status.HTTP_201_CREATED,
)
def post_bus_location(
    bus_id: uuid.UUID,
    data: BusLocationCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Record a GPS point for a bus.

    MVP policy: any authenticated user (passenger, driver, admin, …) may post a
    location for any existing bus. We only reject when the caller is not
    authenticated (handled upstream by `get_current_user`) or when `bus_id`
    does not exist.
    """
    row = buses_crud.get(db, bus_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    return buses_crud.create_location(
        db,
        bus_id=bus_id,
        latitude=data.latitude,
        longitude=data.longitude,
        user_id=current_user.id,
    )


@router.get("/{bus_id}/location", response_model=BusLocationRead)
def get_bus_location(
    bus_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> BusLocation:
    row = buses_crud.get(db, bus_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    loc = buses_crud.get_latest_location(db, bus_id)
    if loc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No location recorded for this bus")
    return loc
