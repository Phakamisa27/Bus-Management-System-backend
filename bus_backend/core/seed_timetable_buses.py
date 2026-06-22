"""
Ensure buses referenced by the frontend timetable exist in the database.

IDs are kept in sync with: Bus-Management-System-fronted/data/timeTable.json
Run automatically on API startup (see main.py lifespan).

Why fresh bus_id values matter
-------------------------------
Earlier seeds reused the same primary keys when routes changed (e.g. Folweni →
Umlazi). The old "insert only if missing" logic then skipped those rows, so the
database kept stale Folweni-era tracking channels while the frontend pointed the
same UUIDs at new routes. Each timetable row now has a v2 UUID; RETIRED_* lists
the old keys that startup sync deletes before inserting the current set.
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
TIMETABLE_BUSES: list[tuple[uuid.UUID, str, str]] = [
    # Umlazi-1-F,G → Westmead
    (uuid.UUID("89452cf7-7dbe-5cbc-a34f-fb8f346850af"), "101", "ZD-101-U1W"),
    (uuid.UUID("de86deff-b13c-57e4-8a48-3af4dae3ed10"), "102", "ZD-102-U1W"),
    (uuid.UUID("aa5f14aa-a4c3-57f6-8456-41f02b9d28d2"), "103", "ZD-103-U1W"),
    (uuid.UUID("66d19aeb-88ca-5960-b3e2-fc32a7ded322"), "104", "ZD-104-U1W"),
    (uuid.UUID("91789eba-991b-5f95-951c-d5a91a970c74"), "105", "ZD-105-U1W"),
    (uuid.UUID("f074e255-6c4b-5aad-856f-8a35051a184d"), "106", "ZD-106-U1W"),
    (uuid.UUID("259631df-49fc-5453-ac89-c7bbd2f426dd"), "107", "ZD-107-U1W"),
    (uuid.UUID("fd2a5490-7401-51a5-ba28-253c7d0aa038"), "108", "ZD-108-U1W"),
    (uuid.UUID("def391f2-184e-53f3-a420-3bf76279f9a8"), "109", "ZD-109-U1W"),
    (uuid.UUID("e7f971fe-05e8-5a23-92eb-d743943204e8"), "110", "ZD-110-U1W"),
    # Umlazi-2-M&R → Westmead
    (uuid.UUID("9966fd39-17b8-52dc-9d6f-3db5fd8a901c"), "201", "ZD-201-U2W"),
    (uuid.UUID("5a971ba7-6765-55cf-b240-619360a9fe39"), "202", "ZD-202-U2W"),
    (uuid.UUID("aaa089d6-48dc-5b20-a25a-16636f583ed3"), "203", "ZD-203-U2W"),
    (uuid.UUID("2d889ac7-f151-50b8-a33e-eaeef8ff15b7"), "204", "ZD-204-U2W"),
    (uuid.UUID("90d404b4-1217-5928-93f6-9643521f6d17"), "205", "ZD-205-U2W"),
    (uuid.UUID("053bf104-06bb-551f-a08b-32bb43128e51"), "206", "ZD-206-U2W"),
    (uuid.UUID("aa675c4e-d88e-5e7d-8462-d905f92614cf"), "207", "ZD-207-U2W"),
    (uuid.UUID("fb8c9e21-534c-5ba1-9299-b9e73107f333"), "208", "ZD-208-U2W"),
    (uuid.UUID("2bd2cb1e-be49-54bf-b02f-1bda29e47103"), "209", "ZD-209-U2W"),
    (uuid.UUID("8225cef7-447e-5219-b237-bf199dd288c2"), "210", "ZD-210-U2W"),
    # Umlazi-5-U → Westmead
    (uuid.UUID("16c21edb-ff74-5a86-8189-b086db282da1"), "301", "ZD-301-U5W"),
    (uuid.UUID("b1c941ee-87c6-531b-bfa6-4e6f5b84922f"), "302", "ZD-302-U5W"),
    (uuid.UUID("d9ccc461-19b2-5703-80de-311d04f29e05"), "303", "ZD-303-U5W"),
    (uuid.UUID("334ec26c-698f-5906-a17b-23caaac35bb2"), "304", "ZD-304-U5W"),
    (uuid.UUID("dc40d2de-00da-5d61-9032-a2a45a156db4"), "305", "ZD-305-U5W"),
    (uuid.UUID("6de45006-3988-50af-8fbf-aa6ac4ba0663"), "306", "ZD-306-U5W"),
    (uuid.UUID("b8f71563-5359-5c67-8595-d666170880aa"), "307", "ZD-307-U5W"),
    (uuid.UUID("5a1b8a83-76f3-56ba-a8b8-9f3e4715fe68"), "308", "ZD-308-U5W"),
    (uuid.UUID("dc71534f-a949-53c2-8ff3-c7ad00a701f1"), "309", "ZD-309-U5W"),
    (uuid.UUID("80f9b19f-9b97-5a57-8cfa-c6031619eb54"), "310", "ZD-310-U5W"),
    # Westmead → Umlazi-1-F,G
    (uuid.UUID("838190b3-a2ab-56b6-b025-1f1b66f9d4ba"), "401", "ZD-401-WU1"),
    (uuid.UUID("db3d1f28-203e-52e1-82d8-7eaf1c45f068"), "402", "ZD-402-WU1"),
    (uuid.UUID("a7153523-a1ef-5607-bcbc-a631f2a6a77b"), "403", "ZD-403-WU1"),
    (uuid.UUID("1887481e-07a1-519a-974f-7631f135742d"), "404", "ZD-404-WU1"),
    (uuid.UUID("e858e705-ee8e-5042-9951-8212e366f85e"), "405", "ZD-405-WU1"),
    (uuid.UUID("485b8e31-45bc-5387-84e2-07827eeb5cbb"), "406", "ZD-406-WU1"),
    (uuid.UUID("b146c3af-c0be-5355-bb3f-d990bc5362dc"), "407", "ZD-407-WU1"),
    (uuid.UUID("fa782bbc-acf1-5c4c-b271-c76d2067d359"), "408", "ZD-408-WU1"),
    (uuid.UUID("e344dadf-18b5-5096-96af-dbe87b97ba93"), "409", "ZD-409-WU1"),
    (uuid.UUID("b4662588-f982-5607-8fba-761401b7c15a"), "410", "ZD-410-WU1"),
    # Westmead → Umlazi-2-M&R
    (uuid.UUID("9ad541f5-9ec6-5dec-b534-bfa42084d5c8"), "501", "ZD-501-WU2"),
    (uuid.UUID("4f9d19f6-f53f-5a18-9e30-12d54d308970"), "502", "ZD-502-WU2"),
    (uuid.UUID("862766c2-1585-5152-bfb8-c91fbf69ed74"), "503", "ZD-503-WU2"),
    (uuid.UUID("c8fb5f31-b7b1-5c0b-ae4c-f2406e9bb043"), "504", "ZD-504-WU2"),
    (uuid.UUID("e2a9b179-25b6-5481-bb0e-9c88d2124620"), "505", "ZD-505-WU2"),
    (uuid.UUID("ea13cdee-6404-590d-b88f-b223b41fd161"), "506", "ZD-506-WU2"),
    (uuid.UUID("fe038265-e6f1-5a44-9b45-8521151e5bf2"), "507", "ZD-507-WU2"),
    (uuid.UUID("2c3c4e6a-9d4b-5dc1-b04b-ae6315beebaf"), "508", "ZD-508-WU2"),
    (uuid.UUID("a3d74efe-eb87-54d8-a5c7-6bfdfc7863bf"), "509", "ZD-509-WU2"),
    (uuid.UUID("08e785a1-a0c2-5517-8b1f-2b81670d2b7f"), "510", "ZD-510-WU2"),
    # Westmead → Umlazi-5-U
    (uuid.UUID("ee0bc209-3773-5f3b-ba3e-b9d44ca750bf"), "601", "ZD-601-WU5"),
    (uuid.UUID("4200fbbd-0f36-588d-b098-bc3fceea58ef"), "602", "ZD-602-WU5"),
    (uuid.UUID("c5c90890-a555-5f6c-bce0-47122fc6f5a1"), "603", "ZD-603-WU5"),
    (uuid.UUID("95f260e2-ec49-5074-91eb-1847ed114404"), "604", "ZD-604-WU5"),
    (uuid.UUID("43485cfe-da97-59fc-834b-59df9d020755"), "605", "ZD-605-WU5"),
    (uuid.UUID("38618a8b-589b-5c77-a6be-6b6c683481be"), "606", "ZD-606-WU5"),
    (uuid.UUID("a3e59d92-561c-57c7-8e88-db251de9d1e6"), "607", "ZD-607-WU5"),
    (uuid.UUID("4a8a8b3a-98f3-58f1-8456-167730942f33"), "608", "ZD-608-WU5"),
    (uuid.UUID("1a63a8c1-00be-558f-b7ab-aba42efa00a6"), "609", "ZD-609-WU5"),
    (uuid.UUID("15308d1e-c1f3-58d3-9cc9-da1c6d985605"), "610", "ZD-610-WU5"),
]

# Folweni / Durban / Jacobs era — never reuse these tracking channels.
RETIRED_TIMETABLE_BUS_IDS: frozenset[uuid.UUID] = frozenset(
    uuid.UUID(value)
    for value in (
        "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c01",
        "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c02",
        "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c03",
        "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c04",
        "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c05",
        "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c06",
        "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c07",
        "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c08",
        "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c09",
        "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c10",
        "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d01",
        "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d02",
        "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d03",
        "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d04",
        "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d05",
        "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d06",
        "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d07",
        "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d08",
        "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d09",
        "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d10",
        "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e01",
        "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e02",
        "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e03",
        "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e04",
        "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e05",
        "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e06",
        "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e07",
        "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e08",
        "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e09",
        "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e10",
        "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f01",
        "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f02",
        "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f03",
        "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f04",
        "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f05",
        "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f06",
        "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f07",
        "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f08",
        "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f09",
        "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f10",
        "e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a01",
        "e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a02",
        "e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a03",
        "e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a04",
        "e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a05",
        "e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a06",
        "e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a07",
        "e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a08",
        "e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a09",
        "e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a10",
        "f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b01",
        "f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b02",
        "f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b03",
        "f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b04",
        "f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b05",
        "f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b06",
        "f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b07",
        "f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b08",
        "f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b09",
        "f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b10",
    )
)

# Folweni-era seed plate suffixes (e.g. ZD-201-FW = Folweni → Westmead).
RETIRED_PLATE_SUFFIXES: frozenset[str] = frozenset({"FD", "DF", "FW", "WF", "FJ", "JF"})

SEED_USER_EMAIL = "timetable-seed@local.dev"
SEED_COMPANY_NAME = "Timetable demo company"


def _valid_bus_ids() -> frozenset[uuid.UUID]:
    return frozenset(bus_id for bus_id, _, _ in TIMETABLE_BUSES)


def _resolve_company_id(db: Session) -> uuid.UUID:
    """Prefer company_id from existing timetable buses to avoid unnecessary Company loads."""
    for query in (
        select(Bus.company_id).where(Bus.id.in_(_valid_bus_ids())).limit(1),
        select(Bus.company_id).where(Bus.id.in_(RETIRED_TIMETABLE_BUS_IDS)).limit(1),
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


def _has_retired_plate(plate_number: str) -> bool:
    if not plate_number.startswith("ZD-"):
        return False
    suffix = plate_number.rsplit("-", 1)[-1]
    return suffix in RETIRED_PLATE_SUFFIXES


def _is_timetable_seed_bus(bus: Bus, valid_ids: frozenset[uuid.UUID]) -> bool:
    if bus.id in RETIRED_TIMETABLE_BUS_IDS:
        return True
    if bus.id in valid_ids:
        return True
    return bus.route_id is None and bus.plate_number.startswith("ZD-")


def _remove_stale_seed_bus(db: Session, bus: Bus) -> None:
    db.execute(delete(BusLocation).where(BusLocation.bus_id == bus.id))
    db.execute(update(Timetable).where(Timetable.bus_id == bus.id).values(bus_id=None))
    db.delete(bus)


def _remove_retired_timetable_buses(db: Session, valid_ids: frozenset[uuid.UUID]) -> int:
    removed = 0

    retired_rows = db.scalars(select(Bus).where(Bus.id.in_(RETIRED_TIMETABLE_BUS_IDS))).all()
    for bus in retired_rows:
        _remove_stale_seed_bus(db, bus)
        removed += 1

    legacy_plate_rows = db.scalars(
        select(Bus).where(
            Bus.route_id.is_(None),
            Bus.plate_number.startswith("ZD-"),
            Bus.id.not_in(valid_ids),
        ),
    ).all()
    for bus in legacy_plate_rows:
        if bus.id in valid_ids or bus.id in RETIRED_TIMETABLE_BUS_IDS:
            continue
        if not (_has_retired_plate(bus.plate_number) or _is_timetable_seed_bus(bus, valid_ids)):
            continue
        _remove_stale_seed_bus(db, bus)
        removed += 1

    return removed


def seed_timetable_buses_if_missing() -> None:
    """Delete retired timetable buses, then upsert the current frontend timetable set."""
    db = SessionLocal()
    try:
        valid_ids = _valid_bus_ids()
        company_id: uuid.UUID | None = None
        created = 0
        updated = 0
        removed = _remove_retired_timetable_buses(db, valid_ids)

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
