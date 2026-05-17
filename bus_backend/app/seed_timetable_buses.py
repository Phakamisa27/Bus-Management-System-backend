"""
Ensure buses referenced by the frontend timetable exist in the database.

IDs are kept in sync with: Bus-Management-System-fronted/data/timeTable.json
Run automatically on API startup (see main.py lifespan).
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from bus_backend.app.models import Bus, BusStatus, Company, User, UserRole
from bus_backend.core.auth import hash_password
from bus_backend.core.database import SessionLocal

logger = logging.getLogger(__name__)

# Must match bus_id values in data/timeTable.json — one unique row per timetable entry.
TIMETABLE_BUSES: list[tuple[uuid.UUID, str, str]] = [
    (
        uuid.UUID("5e1c3169-a012-44d9-a18c-561f0fff3a10"),
        "200",
        "ZD-200-U1-PM",
    ),
    (
        uuid.UUID("b6f7e2c4-7d3a-4f9b-8e1c-5d6f7a8b9c20"),
        "200",
        "ZD-200-U2-PM",
    ),
    (
        uuid.UUID("c9c4b6d8-2f3a-4b5c-8d9e-1a2b3c4d5e30"),
        "200",
        "ZD-200-U5-PM",
    ),
    (
        uuid.UUID("d3a7b8c9-1e2f-4a5b-9c8d-7e6f5a4b3c40"),
        "200",
        "ZD-200-U1-AM",
    ),
    (
        uuid.UUID("e6d5e4f3-2b1c-4d5e-9f8a-7b6c5d4e3f50"),
        "200",
        "ZD-200-U2-AM",
    ),
    (
        uuid.UUID("f1b2c3d4-5f6a-4b7c-8d9e-0f1a2b3c4d60"),
        "200",
        "ZD-200-U5-AM",
    ),
]

SEED_USER_EMAIL = "timetable-seed@local.dev"


def _resolve_company(db: Session) -> Company:
    existing = db.scalar(select(Company).limit(1))
    if existing is not None:
        return existing

    owner = db.scalar(select(User).limit(1))
    if owner is None:
        owner = User(
            email=SEED_USER_EMAIL,
            full_name="Timetable seed owner",
            hashed_password=hash_password("unused-change-in-production"),
            role=UserRole.admin,
        )
        db.add(owner)
        db.commit()
        db.refresh(owner)

    company = Company(
        owner_id=owner.id,
        name="Timetable demo company",
        address="",
        phone="",
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def seed_timetable_buses_if_missing() -> None:
    """Create timetable buses with fixed primary keys when they are not already present."""
    db = SessionLocal()
    try:
        company = _resolve_company(db)
        created = 0
        for bus_id, bus_number, plate in TIMETABLE_BUSES:
            if db.get(Bus, bus_id) is not None:
                continue
            db.add(
                Bus(
                    id=bus_id,
                    company_id=company.id,
                    route_id=None,
                    bus_number=bus_number,
                    plate_number=plate,
                    capacity=40,
                    status=BusStatus.active,
                ),
            )
            created += 1
        if created:
            db.commit()
            logger.info(
                "seed_timetable_buses: inserted %s bus row(s) for timetable frontend",
                created,
            )
    except Exception:
        db.rollback()
        logger.exception("seed_timetable_buses: failed (API will still run)")
    finally:
        db.close()
