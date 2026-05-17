"""Route (bus line) CRUD — database operations for the `Route` model."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from bus_backend.app.schemas import RouteCreate
from bus_backend.app.models import Route


def list_routes(db: Session, skip: int = 0, limit: int = 100) -> list[Route]:
    q = select(Route).order_by(Route.name.asc()).offset(skip).limit(limit)
    return list(db.scalars(q).all())


def get(db: Session, route_id: uuid.UUID) -> Route | None:
    return db.get(Route, route_id)


def create(db: Session, data: RouteCreate) -> Route:
    row = Route(
        name=data.name,
        start_lat=data.start_lat,
        start_lng=data.start_lng,
        end_lat=data.end_lat,
        end_lng=data.end_lng,
        stops=data.stops or [],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete(db: Session, route: Route) -> None:
    db.delete(route)
    db.commit()
