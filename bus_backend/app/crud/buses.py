"""Bus CRUD."""

import uuid

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.schemas import BusCreate, BusUpdate
from app.models import Bus, BusLocation


def list_for_company(db: Session, company_id: uuid.UUID) -> list[Bus]:
    q = select(Bus).where(Bus.company_id == company_id).order_by(Bus.bus_number)
    return list(db.scalars(q).all())


def list_all(db: Session, skip: int = 0, limit: int = 100) -> list[Bus]:
    q = select(Bus).order_by(Bus.bus_number.asc()).offset(skip).limit(limit)
    return list(db.scalars(q).all())


def get(db: Session, bus_id: uuid.UUID) -> Bus | None:
    return db.get(Bus, bus_id)


def create(db: Session, data: BusCreate) -> Bus:
    row = Bus(
        company_id=data.company_id,
        route_id=data.route_id,
        bus_number=data.bus_number,
        plate_number=data.plate_number,
        capacity=data.capacity,
        status=data.status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update(db: Session, bus: Bus, data: BusUpdate) -> Bus:
    if data.route_id is not None:
        bus.route_id = data.route_id
    if data.bus_number is not None:
        bus.bus_number = data.bus_number
    if data.plate_number is not None:
        bus.plate_number = data.plate_number
    if data.capacity is not None:
        bus.capacity = data.capacity
    if data.status is not None:
        bus.status = data.status
    db.commit()
    db.refresh(bus)
    return bus


def delete(db: Session, bus: Bus) -> None:
    db.delete(bus)
    db.commit()


def create_location(
    db: Session,
    *,
    bus_id: uuid.UUID,
    latitude: float,
    longitude: float,
    user_id: uuid.UUID,
) -> BusLocation:
    row = BusLocation(
        bus_id=bus_id,
        latitude=latitude,
        longitude=longitude,
        user_id=user_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_latest_location(db: Session, bus_id: uuid.UUID) -> BusLocation | None:
    q = (
        select(BusLocation)
        .where(BusLocation.bus_id == bus_id)
        .order_by(desc(BusLocation.timestamp))
        .limit(1)
    )
    return db.scalars(q).first()
