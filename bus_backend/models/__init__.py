"""
All SQLAlchemy models in one module (easy to browse when learning).

Requires PostgreSQL with PostGIS extension for the optional `geom` column on `Route`.
Run once on the DB:  CREATE EXTENSION IF NOT EXISTS postgis;
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, time
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    admin = "admin"
    driver = "driver"
    passenger = "passenger"


class BusStatus(str, enum.Enum):
    active = "active"
    offline = "offline"
    maintenance = "maintenance"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False, length=32),
        default=UserRole.passenger,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    companies: Mapped[list[Company]] = relationship(
        back_populates="owner",
        foreign_keys="Company.owner_id",
    )
    bus_locations: Mapped[list["BusLocation"]] = relationship(back_populates="user")
    password_resets: Mapped[list["PasswordReset"]] = relationship(back_populates="user")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(64), default="")
    address: Mapped[str] = mapped_column(String(512), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    number_of_buses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    main_routes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    owner: Mapped[User] = relationship(back_populates="companies", foreign_keys=[owner_id])
    buses: Mapped[list[Bus]] = relationship(back_populates="company")


class Route(Base):
    """
    A route between two endpoints. `stops` holds extra JSON data (e.g. stop names).
    `geom` is an optional PostGIS LineString (SRID 4326) for drawing on a map.
    """

    __tablename__ = "routes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    start_lat: Mapped[float] = mapped_column(Float, nullable=False)
    start_lng: Mapped[float] = mapped_column(Float, nullable=False)
    end_lat: Mapped[float] = mapped_column(Float, nullable=False)
    end_lng: Mapped[float] = mapped_column(Float, nullable=False)
    stops: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    geom: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=True),
        nullable=True,
    )

    buses: Mapped[list[Bus]] = relationship(back_populates="route")
    timetables: Mapped[list[Timetable]] = relationship(back_populates="route")


class Bus(Base):
    __tablename__ = "buses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True)
    route_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("routes.id"),
        nullable=True,
        index=True,
    )
    bus_number: Mapped[str] = mapped_column(String(64), nullable=False)
    plate_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    status: Mapped[BusStatus] = mapped_column(
        Enum(BusStatus, name="bus_status", native_enum=False, length=32),
        default=BusStatus.active,
    )

    company: Mapped[Company] = relationship(back_populates="buses")
    route: Mapped[Route | None] = relationship(back_populates="buses")
    timetables: Mapped[list[Timetable]] = relationship(back_populates="bus")
    locations: Mapped[list["BusLocation"]] = relationship(back_populates="bus")


class Timetable(Base):
    """
    One scheduled trip pattern: which route, optional bus, weekday, departure/arrival times.
    `day_of_week`: 0 = Monday ... 6 = Sunday (same as Python's weekday()).
    """

    __tablename__ = "timetables"
    __table_args__ = (UniqueConstraint("route_id", "day_of_week", "depart_time", name="uq_timetable_slot"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("routes.id"), index=True)
    bus_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buses.id"),
        nullable=True,
        index=True,
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-6
    depart_time: Mapped[time] = mapped_column(Time, nullable=False)
    arrive_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    route: Mapped[Route] = relationship(back_populates="timetables")
    bus: Mapped[Bus | None] = relationship(back_populates="timetables")


class BusLocation(Base):
    """Point-in-time GPS reading for a bus, associated with the reporting user."""

    __tablename__ = "bus_locations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bus_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("buses.id"), index=True, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)

    bus: Mapped[Bus] = relationship(back_populates="locations")
    user: Mapped[User] = relationship(back_populates="bus_locations")


class PasswordReset(Base):
    """One password-reset request: a single-use token with an expiry time."""

    __tablename__ = "password_resets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="password_resets")
