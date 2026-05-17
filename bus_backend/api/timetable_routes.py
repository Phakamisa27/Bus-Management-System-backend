"""Timetable entries (linked to a route and optional bus)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from bus_backend.app.crud import companies as companies_crud
from bus_backend.app.schemas import TimetableCreate, TimetableRead, TimetableUpdate
from bus_backend.app.database import get_db
from bus_backend.app.models import Bus, Timetable, User
from bus_backend.core.auth import get_current_user

router = APIRouter(prefix="/timetables", tags=["timetables"])


def _can_touch_bus(db: Session, bus: Bus, user: User) -> bool:
    company = companies_crud.get(db, bus.company_id)
    return company is not None and company.owner_id == user.id


@router.get("", response_model=list[TimetableRead])
def list_timetables(
    db: Annotated[Session, Depends(get_db)],
    route_id: Annotated[uuid.UUID | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[Timetable]:
    q = select(Timetable).order_by(
        Timetable.day_of_week,
        Timetable.depart_time,
    )
    if route_id is not None:
        q = q.where(Timetable.route_id == route_id)
    q = q.offset(skip).limit(limit)
    return list(db.scalars(q).all())


@router.post("", response_model=TimetableRead, status_code=status.HTTP_201_CREATED)
def create_timetable(
    data: TimetableCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Timetable:
    if data.bus_id is not None:
        bus = db.get(Bus, data.bus_id)
        if bus is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
        if not _can_touch_bus(db, bus, current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this bus")

    row = Timetable(
        route_id=data.route_id,
        bus_id=data.bus_id,
        day_of_week=data.day_of_week,
        depart_time=data.depart_time,
        arrive_time=data.arrive_time,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        is_active=data.is_active,
        notes=data.notes,
    )
    db.add(row)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create timetable (duplicate slot or invalid data?)",
        ) from None
    db.refresh(row)
    return row


@router.get("/{timetable_id}", response_model=TimetableRead)
def get_timetable(
    timetable_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Timetable:
    row = db.get(Timetable, timetable_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable not found")
    return row


@router.patch("/{timetable_id}", response_model=TimetableRead)
def update_timetable(
    timetable_id: uuid.UUID,
    data: TimetableUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Timetable:
    row = db.get(Timetable, timetable_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable not found")

    updates = data.model_dump(exclude_unset=True)
    if "bus_id" in updates:
        new_bus_id = updates["bus_id"]
        if new_bus_id is not None:
            bus = db.get(Bus, new_bus_id)
            if bus is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
            if not _can_touch_bus(db, bus, current_user):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this bus")
        row.bus_id = new_bus_id
    for key in ("day_of_week", "depart_time", "arrive_time", "valid_from", "valid_until", "is_active", "notes"):
        if key in updates:
            setattr(row, key, updates[key])

    db.commit()
    db.refresh(row)
    return row


@router.delete("/{timetable_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_timetable(
    timetable_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    row = db.get(Timetable, timetable_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable not found")
    if row.bus_id is not None:
        bus = db.get(Bus, row.bus_id)
        if bus is not None and not _can_touch_bus(db, bus, current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    db.delete(row)
    db.commit()
