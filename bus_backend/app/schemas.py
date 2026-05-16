"""Pydantic models for request/response validation (API layer)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import BusStatus, UserRole


# --- Auth & User ---


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.passenger


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# --- Company ---


class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: str = ""
    phone: str = ""


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    address: str | None = None
    phone: str | None = None


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime


# --- Route ---


class RouteBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    stops: list = Field(default_factory=list)


class RouteCreate(RouteBase):
    pass


class RouteRead(RouteBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


# --- Bus ---


class BusBase(BaseModel):
    bus_number: str = Field(..., max_length=64)
    plate_number: str = Field(..., max_length=32)
    capacity: int = Field(40, ge=1)
    status: BusStatus = BusStatus.active


class BusCreate(BusBase):
    company_id: uuid.UUID
    route_id: uuid.UUID | None = None


class BusUpdate(BaseModel):
    route_id: uuid.UUID | None = None
    bus_number: str | None = Field(None, max_length=64)
    plate_number: str | None = Field(None, max_length=32)
    capacity: int | None = Field(None, ge=1)
    status: BusStatus | None = None


class BusRead(BusBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    route_id: uuid.UUID | None


class BusLocationCreate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class BusLocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bus_id: uuid.UUID
    latitude: float
    longitude: float
    timestamp: datetime
    user_id: uuid.UUID


# --- Timetable ---


class TimetableBase(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday ... 6=Sunday")
    depart_time: time
    arrive_time: time | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    is_active: bool = True
    notes: str = ""


class TimetableCreate(TimetableBase):
    route_id: uuid.UUID
    bus_id: uuid.UUID | None = None


class TimetableUpdate(BaseModel):
    bus_id: uuid.UUID | None = None
    day_of_week: int | None = Field(None, ge=0, le=6)
    depart_time: time | None = None
    arrive_time: time | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    is_active: bool | None = None
    notes: str | None = None


class TimetableRead(TimetableBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    route_id: uuid.UUID
    bus_id: uuid.UUID | None
    created_at: datetime
