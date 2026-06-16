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
# Each entry below is an independent tracking channel: a passenger sharing GPS for
# one bus_id never affects what viewers see on a different bus_id.
TIMETABLE_BUSES: list[tuple[uuid.UUID, str, str]] = [
    # Folweni to Durban
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c01"), "101", "ZD-101-FD"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c02"), "102", "ZD-102-FD"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c03"), "103", "ZD-103-FD"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c04"), "104", "ZD-104-FD"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c05"), "105", "ZD-105-FD"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c06"), "106", "ZD-106-FD"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c07"), "107", "ZD-107-FD"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c08"), "108", "ZD-108-FD"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c09"), "109", "ZD-109-FD"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c10"), "110", "ZD-110-FD"),
    # Durban to Folweni
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f01"), "401", "ZD-401-DF"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f02"), "402", "ZD-402-DF"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f03"), "403", "ZD-403-DF"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f04"), "404", "ZD-404-DF"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f05"), "405", "ZD-405-DF"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f06"), "406", "ZD-406-DF"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f07"), "407", "ZD-407-DF"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f08"), "408", "ZD-408-DF"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f09"), "409", "ZD-409-DF"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f10"), "410", "ZD-410-DF"),
    # Folweni to Westmead
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d01"), "201", "ZD-201-FW"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d02"), "202", "ZD-202-FW"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d03"), "203", "ZD-203-FW"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d04"), "204", "ZD-204-FW"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d05"), "205", "ZD-205-FW"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d06"), "206", "ZD-206-FW"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d07"), "207", "ZD-207-FW"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d08"), "208", "ZD-208-FW"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d09"), "209", "ZD-209-FW"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d10"), "210", "ZD-210-FW"),
    # Westmead to Folweni
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a01"), "501", "ZD-501-WF"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a02"), "502", "ZD-502-WF"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a03"), "503", "ZD-503-WF"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a04"), "504", "ZD-504-WF"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a05"), "505", "ZD-505-WF"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a06"), "506", "ZD-506-WF"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a07"), "507", "ZD-507-WF"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a08"), "508", "ZD-508-WF"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a09"), "509", "ZD-509-WF"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a10"), "510", "ZD-510-WF"),
    # Folweni to Jacobs
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e01"), "301", "ZD-301-FJ"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e02"), "302", "ZD-302-FJ"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e03"), "303", "ZD-303-FJ"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e04"), "304", "ZD-304-FJ"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e05"), "305", "ZD-305-FJ"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e06"), "306", "ZD-306-FJ"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e07"), "307", "ZD-307-FJ"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e08"), "308", "ZD-308-FJ"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e09"), "309", "ZD-309-FJ"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e10"), "310", "ZD-310-FJ"),
    # Jacobs to Folweni
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b01"), "601", "ZD-601-JF"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b02"), "602", "ZD-602-JF"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b03"), "603", "ZD-603-JF"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b04"), "604", "ZD-604-JF"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b05"), "605", "ZD-605-JF"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b06"), "606", "ZD-606-JF"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b07"), "607", "ZD-607-JF"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b08"), "608", "ZD-608-JF"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b09"), "609", "ZD-609-JF"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b10"), "610", "ZD-610-JF"),
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
