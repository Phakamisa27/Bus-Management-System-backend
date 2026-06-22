"""
Ensure buses referenced by the frontend timetable exist in the database.

IDs are kept in sync with: Bus-Management-System-fronted/data/timeTable.json
Run automatically on API startup (see main.py lifespan).
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from bus_backend.app.models import Bus, BusLocation, BusStatus, Company, Timetable, User, UserRole
from bus_backend.core.auth import hash_password
from bus_backend.core.database import SessionLocal

logger = logging.getLogger(__name__)

# Must match bus_id values in data/timeTable.json — one unique row per timetable entry.
# Each entry below is an independent tracking channel: a passenger sharing GPS for
# one bus_id never affects what viewers see on a different bus_id.
TIMETABLE_BUSES: list[tuple[uuid.UUID, str, str]] = [
    # Umlazi-1-F,G → Westmead
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c01"), "101", "ZD-101-U1W"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c02"), "102", "ZD-102-U1W"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c03"), "103", "ZD-103-U1W"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c04"), "104", "ZD-104-U1W"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c05"), "105", "ZD-105-U1W"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c06"), "106", "ZD-106-U1W"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c07"), "107", "ZD-107-U1W"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c08"), "108", "ZD-108-U1W"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c09"), "109", "ZD-109-U1W"),
    (uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c10"), "110", "ZD-110-U1W"),
    # Umlazi-2-M&R → Westmead
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d01"), "201", "ZD-201-U2W"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d02"), "202", "ZD-202-U2W"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d03"), "203", "ZD-203-U2W"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d04"), "204", "ZD-204-U2W"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d05"), "205", "ZD-205-U2W"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d06"), "206", "ZD-206-U2W"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d07"), "207", "ZD-207-U2W"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d08"), "208", "ZD-208-U2W"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d09"), "209", "ZD-209-U2W"),
    (uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d10"), "210", "ZD-210-U2W"),
    # Umlazi-5-U → Westmead
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e01"), "301", "ZD-301-U5W"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e02"), "302", "ZD-302-U5W"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e03"), "303", "ZD-303-U5W"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e04"), "304", "ZD-304-U5W"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e05"), "305", "ZD-305-U5W"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e06"), "306", "ZD-306-U5W"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e07"), "307", "ZD-307-U5W"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e08"), "308", "ZD-308-U5W"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e09"), "309", "ZD-309-U5W"),
    (uuid.UUID("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e10"), "310", "ZD-310-U5W"),
    # Westmead → Umlazi-1-F,G
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f01"), "401", "ZD-401-WU1"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f02"), "402", "ZD-402-WU1"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f03"), "403", "ZD-403-WU1"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f04"), "404", "ZD-404-WU1"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f05"), "405", "ZD-405-WU1"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f06"), "406", "ZD-406-WU1"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f07"), "407", "ZD-407-WU1"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f08"), "408", "ZD-408-WU1"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f09"), "409", "ZD-409-WU1"),
    (uuid.UUID("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f10"), "410", "ZD-410-WU1"),
    # Westmead → Umlazi-2-M&R
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a01"), "501", "ZD-501-WU2"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a02"), "502", "ZD-502-WU2"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a03"), "503", "ZD-503-WU2"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a04"), "504", "ZD-504-WU2"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a05"), "505", "ZD-505-WU2"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a06"), "506", "ZD-506-WU2"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a07"), "507", "ZD-507-WU2"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a08"), "508", "ZD-508-WU2"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a09"), "509", "ZD-509-WU2"),
    (uuid.UUID("e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a10"), "510", "ZD-510-WU2"),
    # Westmead → Umlazi-5-U
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b01"), "601", "ZD-601-WU5"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b02"), "602", "ZD-602-WU5"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b03"), "603", "ZD-603-WU5"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b04"), "604", "ZD-604-WU5"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b05"), "605", "ZD-605-WU5"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b06"), "606", "ZD-606-WU5"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b07"), "607", "ZD-607-WU5"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b08"), "608", "ZD-608-WU5"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b09"), "609", "ZD-609-WU5"),
    (uuid.UUID("f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b10"), "610", "ZD-610-WU5"),
]

# Fixed IDs from prior Folweni-era timetable seeds (same UUIDs, reused for Umlazi routes).
LEGACY_TIMETABLE_BUS_IDS: frozenset[uuid.UUID] = frozenset(bus_id for bus_id, _, _ in TIMETABLE_BUSES)

SEED_USER_EMAIL = "timetable-seed@local.dev"
SEED_COMPANY_NAME = "Timetable demo company"


def _valid_bus_ids() -> frozenset[uuid.UUID]:
    return frozenset(bus_id for bus_id, _, _ in TIMETABLE_BUSES)


def _resolve_company_id(db: Session) -> uuid.UUID:
    """Prefer company_id from existing timetable buses to avoid unnecessary Company loads."""
    for query in (
        select(Bus.company_id).where(Bus.id.in_(LEGACY_TIMETABLE_BUS_IDS)).limit(1),
        select(Bus.company_id).limit(1),
    ):
        company_id = db.scalar(query)
        if company_id is not None:
            return company_id

    company = _create_seed_company(db)
    return company.id


def _create_seed_company(db: Session) -> Company:
    existing = db.scalar(select(Company).where(Company.name == SEED_COMPANY_NAME).limit(1))
    if existing is not None:
        return existing

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
        name=SEED_COMPANY_NAME,
        address="",
        phone="",
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def _is_legacy_timetable_seed_bus(bus: Bus) -> bool:
    """True only for buses created by this seed module, not company/admin additions."""
    if bus.id in LEGACY_TIMETABLE_BUS_IDS:
        return True
    return bus.route_id is None and bus.plate_number.startswith("ZD-")


def _remove_stale_seed_bus(db: Session, bus: Bus) -> None:
    db.execute(delete(BusLocation).where(BusLocation.bus_id == bus.id))
    db.execute(update(Timetable).where(Timetable.bus_id == bus.id).values(bus_id=None))
    db.delete(bus)


def seed_timetable_buses_if_missing() -> None:
    """Sync timetable buses: upsert current rows and remove stale seeded buses."""
    db = SessionLocal()
    try:
        valid_ids = _valid_bus_ids()
        company_id: uuid.UUID | None = None
        created = 0
        updated = 0
        removed = 0

        for bus_id, bus_number, plate in TIMETABLE_BUSES:
            existing = db.get(Bus, bus_id)
            if existing is None:
                if company_id is None:
                    company_id = _resolve_company_id(db)
                db.add(
                    Bus(
                        id=bus_id,
                        company_id=company_id,
                        route_id=None,
                        bus_number=bus_number,
                        plate_number=plate,
                        capacity=40,
                        status=BusStatus.active,
                    ),
                )
                created += 1
                continue

            changed = False
            if existing.bus_number != bus_number:
                existing.bus_number = bus_number
                changed = True
            if existing.plate_number != plate:
                existing.plate_number = plate
                changed = True
            if existing.status is not BusStatus.active:
                existing.status = BusStatus.active
                changed = True
            if existing.route_id is not None:
                existing.route_id = None
                changed = True
            if changed:
                updated += 1

        stale_buses = db.scalars(
            select(Bus).where(
                Bus.id.in_(LEGACY_TIMETABLE_BUS_IDS),
                Bus.id.not_in(valid_ids),
            ),
        ).all()
        for bus in stale_buses:
            if _is_legacy_timetable_seed_bus(bus):
                _remove_stale_seed_bus(db, bus)
                removed += 1

        extra_seed_buses = db.scalars(
            select(Bus).where(
                Bus.route_id.is_(None),
                Bus.plate_number.startswith("ZD-"),
                Bus.id.not_in(valid_ids),
            ),
        ).all()
        for bus in extra_seed_buses:
            if bus.id in valid_ids:
                continue
            if not _is_legacy_timetable_seed_bus(bus):
                continue
            _remove_stale_seed_bus(db, bus)
            removed += 1

        if created or updated or removed:
            db.commit()
            logger.info(
                "seed_timetable_buses: created=%s updated=%s removed=%s (valid=%s)",
                created,
                updated,
                removed,
                len(valid_ids),
            )
    except Exception:
        db.rollback()
        logger.exception("seed_timetable_buses: failed (API will still run)")
    finally:
        db.close()
