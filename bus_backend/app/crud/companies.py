"""Company CRUD."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from bus_backend.app.schemas import CompanyCreate, CompanyRegisterRequest, CompanyUpdate
from bus_backend.app.models import Company, User


def list_for_owner(db: Session, owner_id: uuid.UUID) -> list[Company]:
    q = select(Company).where(Company.owner_id == owner_id).order_by(Company.name)
    return list(db.scalars(q).all())


def list_all(db: Session, skip: int = 0, limit: int = 100) -> list[Company]:
    q = select(Company).order_by(Company.created_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(q).all())


def get(db: Session, company_id: uuid.UUID) -> Company | None:
    return db.get(Company, company_id)


def create(db: Session, owner_id: uuid.UUID, data: CompanyCreate) -> Company:
    row = Company(
        owner_id=owner_id,
        name=data.name,
        registration_number=data.registration_number,
        address=data.address,
        phone=data.phone,
        number_of_buses=data.number_of_buses,
        main_routes=data.main_routes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def register_with_admin(db: Session, data: CompanyRegisterRequest) -> tuple[User, Company]:
    """Create an admin user and linked company in one transaction."""
    from bus_backend.app.models import UserRole
    from bus_backend.core.auth import hash_password

    user = User(
        email=str(data.work_email),
        full_name=data.contact_full_name,
        hashed_password=hash_password(data.password),
        role=UserRole.admin,
    )
    db.add(user)
    db.flush()

    company = Company(
        owner_id=user.id,
        name=data.company_name,
        registration_number=(data.registration_number or "").strip(),
        phone=data.phone_number.strip(),
        number_of_buses=data.number_of_buses,
        main_routes=(data.main_routes or "").strip(),
    )
    db.add(company)
    db.commit()
    db.refresh(user)
    db.refresh(company)
    return user, company


def update(db: Session, company: Company, data: CompanyUpdate) -> Company:
    if data.name is not None:
        company.name = data.name
    if data.registration_number is not None:
        company.registration_number = data.registration_number
    if data.address is not None:
        company.address = data.address
    if data.phone is not None:
        company.phone = data.phone
    if data.number_of_buses is not None:
        company.number_of_buses = data.number_of_buses
    if data.main_routes is not None:
        company.main_routes = data.main_routes
    db.commit()
    db.refresh(company)
    return company


def delete(db: Session, company: Company) -> None:
    db.delete(company)
    db.commit()
